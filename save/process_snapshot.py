#!/usr/bin/env python3
"""Process a snapshot markdown file into structured task/memory files. No AI needed."""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def write_yaml(path, data):
    """Write YAML file, falling back to basic formatting if PyYAML not available."""
    if HAS_YAML:
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    else:
        # Basic YAML writer for simple structures
        with open(path, 'w') as f:
            _write_yaml_value(f, data, indent=0)


def _write_yaml_value(f, value, indent=0):
    """Minimal YAML serializer for dicts, lists, and scalars."""
    prefix = "  " * indent
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                f.write(f"{prefix}{k}:\n")
                _write_yaml_value(f, v, indent + 1)
            else:
                f.write(f"{prefix}{k}: {_yaml_scalar(v)}\n")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    if first:
                        f.write(f"{prefix}- {k}: {_yaml_scalar(v)}\n")
                        first = False
                    else:
                        f.write(f"{prefix}  {k}: {_yaml_scalar(v)}\n")
            else:
                f.write(f"{prefix}- {_yaml_scalar(item)}\n")
    else:
        f.write(f"{prefix}{_yaml_scalar(value)}\n")


def _yaml_scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in ':#{}[]|>&*!%@`') or s.startswith('"') or s.startswith("'") or '\n' in s:
        return json.dumps(s)
    return f'"{s}"'


def slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:60]


def parse_snapshot(snapshot_path):
    """Parse snapshot markdown into sections."""
    with open(snapshot_path) as f:
        content = f.read()

    sections = {}
    current_section = None
    current_lines = []

    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(current_lines)
            current_section = line[3:].strip()
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_lines)

    return sections


def parse_task_lines(text):
    """Parse task lines from a section, returning list of {subject, status, subtasks}."""
    tasks = []
    current_task = None

    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped == '- (none detected)':
            continue

        # Top-level task
        indent = len(line) - len(line.lstrip())
        is_checkbox = re.match(r'^-\s*\[([ x])\]\s*(.*)', stripped)
        is_bold = re.match(r'^-\s*\*\*(.*?)\*\*:?\s*(.*)', stripped)
        is_dash = re.match(r'^-\s+(.*)', stripped)

        if indent <= 2:
            if is_checkbox:
                done = is_checkbox.group(1).lower() == 'x'
                subject = is_checkbox.group(2).strip()
                # Remove bold markers
                subject = re.sub(r'\*\*(.*?)\*\*', r'\1', subject)
                current_task = {
                    'subject': subject,
                    'status': 'completed' if done else 'pending',
                    'subtasks': []
                }
                tasks.append(current_task)
            elif is_bold:
                subject = is_bold.group(1).strip()
                desc = is_bold.group(2).strip()
                current_task = {
                    'subject': subject,
                    'description': desc,
                    'status': 'pending',
                    'subtasks': []
                }
                tasks.append(current_task)
            elif is_dash:
                subject = is_dash.group(1).strip()
                subject = re.sub(r'\*\*(.*?)\*\*', r'\1', subject)
                current_task = {
                    'subject': subject,
                    'status': 'pending',
                    'subtasks': []
                }
                tasks.append(current_task)
        elif current_task and indent > 2:
            # Subtask
            sub_check = re.match(r'^-\s*\[([ x])\]\s*(.*)', stripped)
            if sub_check:
                done = sub_check.group(1).lower() == 'x'
                current_task['subtasks'].append({
                    'subject': sub_check.group(2).strip(),
                    'status': 'completed' if done else 'pending'
                })
            elif is_dash:
                current_task['subtasks'].append({
                    'subject': is_dash.group(1).strip(),
                    'status': 'pending'
                })

    return tasks


def write_tasks(target_dir, sections, timestamp, iso_timestamp):
    """Write task files: TASKS.md, tasks.yaml, tasks.json, INDEX.md, subtask dirs."""
    tasks_dir = os.path.join(target_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)

    # Archive existing TASKS.md
    tasks_md = os.path.join(tasks_dir, "TASKS.md")
    if os.path.exists(tasks_md):
        archive = os.path.join(tasks_dir, f"TASKS_{timestamp}.md")
        shutil.copy2(tasks_md, archive)

    # Parse tasks from snapshot sections
    in_progress = parse_task_lines(sections.get('Tasks - In Progress', sections.get('Tasks — In Progress', '')))
    for t in in_progress:
        t['status'] = 'in_progress'

    pending = parse_task_lines(sections.get('Tasks - Pending', sections.get('Tasks — Pending', '')))
    for t in pending:
        if t['status'] != 'completed':
            t['status'] = 'pending'

    completed = parse_task_lines(sections.get('Tasks - Completed (recent)', sections.get('Tasks — Completed (recent)', '')))
    for t in completed:
        t['status'] = 'completed'

    # Write TASKS.md
    with open(tasks_md, 'w') as f:
        f.write("## In Progress\n")
        for t in in_progress:
            f.write(f"- [ ] **{t['subject']}**")
            if t.get('description'):
                f.write(f": {t['description']}")
            f.write("\n")
            for st in t.get('subtasks', []):
                mark = 'x' if st['status'] == 'completed' else ' '
                f.write(f"  - [{mark}] {st['subject']}\n")
        if not in_progress:
            f.write("- (none)\n")
        f.write("\n")

        f.write("## Pending\n")
        for t in pending:
            f.write(f"- [ ] **{t['subject']}**")
            if t.get('description'):
                f.write(f": {t['description']}")
            f.write("\n")
        if not pending:
            f.write("- (none)\n")
        f.write("\n")

        f.write("## Completed (recent)\n")
        for t in completed:
            f.write(f"- [x] **{t['subject']}**")
            if t.get('description'):
                f.write(f": {t['description']}")
            f.write("\n")
        if not completed:
            f.write("- (none)\n")
        f.write("\n")

    # Build structured data
    def task_to_dict(t, target_dir):
        slug = slugify(t['subject'])
        d = {
            'subject': t['subject'],
            'status': t['status'],
            'slug': slug,
        }
        if t.get('description'):
            d['description'] = t['description']
        if t.get('subtasks'):
            d['subtasks_dir'] = os.path.join(target_dir, "tasks", slug)
            d['subtasks'] = [{'subject': s['subject'], 'status': s['status']} for s in t['subtasks']]
        return d

    data = {
        'last_synced': iso_timestamp,
        'tasks': {
            'in_progress': [task_to_dict(t, target_dir) for t in in_progress],
            'pending': [task_to_dict(t, target_dir) for t in pending],
            'completed': [task_to_dict(t, target_dir) for t in completed],
        }
    }

    # Write tasks.yaml
    write_yaml(os.path.join(tasks_dir, "tasks.yaml"), data)

    # Write tasks.json
    with open(os.path.join(tasks_dir, "tasks.json"), 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

    # Write subtask directories for active tasks
    for t in in_progress + pending:
        if not t.get('subtasks'):
            continue
        slug = slugify(t['subject'])
        sub_dir = os.path.join(tasks_dir, slug)
        os.makedirs(sub_dir, exist_ok=True)

        sub_data = {
            'parent_task': t['subject'],
            'subtasks': [{'subject': s['subject'], 'status': s['status']} for s in t['subtasks']]
        }

        write_yaml(os.path.join(sub_dir, "tasks.yaml"), sub_data)
        with open(os.path.join(sub_dir, "tasks.json"), 'w') as f:
            json.dump(sub_data, f, indent=2)
            f.write('\n')

        with open(os.path.join(sub_dir, "TASKS.md"), 'w') as f:
            f.write(f"# {t['subject']}\n\n")
            for st in t['subtasks']:
                mark = 'x' if st['status'] == 'completed' else ' '
                f.write(f"- [{mark}] {st['subject']}\n")

    # Write INDEX.md
    history = sorted(
        [f for f in os.listdir(tasks_dir) if re.match(r'TASKS_\d+_\d+\.md', f)],
        reverse=True
    )
    with open(os.path.join(tasks_dir, "INDEX.md"), 'w') as f:
        f.write("## Current\n")
        f.write("- [TASKS.md](./TASKS.md)\n")
        f.write("- [tasks.yaml](./tasks.yaml)\n")
        f.write("- [tasks.json](./tasks.json)\n\n")
        f.write("## History\n")
        for h in history:
            f.write(f"- [{h}](./{h})\n")


def write_memory(target_dir, sections, timestamp, iso_timestamp):
    """Write memory files: MEMORY.md, memory.yaml, memory.json, INDEX.md."""
    memory_dir = os.path.join(target_dir, "memory")
    os.makedirs(memory_dir, exist_ok=True)

    # Archive existing MEMORY.md
    memory_md = os.path.join(memory_dir, "MEMORY.md")
    if os.path.exists(memory_md):
        archive = os.path.join(memory_dir, f"MEMORY_{timestamp}.md")
        shutil.copy2(memory_md, archive)

    # Gather context
    key_context = sections.get('Key Context / Memory', sections.get('Key Context', ''))
    prev_memory = sections.get('Previous Memory', '')
    file_paths = sections.get('Important File Paths', '')

    # Parse context lines
    context_items = []
    for line in key_context.split('\n'):
        line = line.strip()
        if line and line.startswith('- '):
            context_items.append(line[2:])

    # Parse file paths
    files = []
    for line in file_paths.split('\n'):
        line = line.strip()
        if line and line.startswith('- '):
            parts = line[2:].split(':', 1)
            if len(parts) == 2:
                files.append({'path': parts[0].strip(), 'description': parts[1].strip()})
            else:
                files.append({'path': parts[0].strip(), 'description': ''})

    # Write MEMORY.md
    with open(memory_md, 'w') as f:
        f.write("# Memory\n\n")
        f.write("## Key Context\n")
        for item in context_items:
            f.write(f"- {item}\n")
        if not context_items:
            f.write("- (none)\n")
        f.write("\n")

        if prev_memory.strip():
            f.write("## Previous Context\n")
            f.write(prev_memory.strip())
            f.write("\n\n")

        f.write("## Important Files\n")
        for fp in files:
            if fp['description']:
                f.write(f"- {fp['path']}: {fp['description']}\n")
            else:
                f.write(f"- {fp['path']}\n")
        if not files:
            f.write("- (none)\n")
        f.write("\n")

    # Build structured data
    data = {
        'timestamp': iso_timestamp,
        'project': target_dir,
        'context': ' '.join(context_items[:3]) if context_items else '',
        'active_work': context_items[:10],
        'key_decisions': [],
        'important_files': files,
        'debugging_insights': [],
        'user_preferences': [],
    }

    # Write memory.yaml
    write_yaml(os.path.join(memory_dir, "memory.yaml"), data)

    # Write memory.json
    with open(os.path.join(memory_dir, "memory.json"), 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

    # Write INDEX.md
    history = sorted(
        [f for f in os.listdir(memory_dir) if re.match(r'MEMORY_\d+_\d+\.md', f)],
        reverse=True
    )
    with open(os.path.join(memory_dir, "INDEX.md"), 'w') as f:
        f.write("## Current\n")
        f.write("- [MEMORY.md](./MEMORY.md)\n")
        f.write("- [memory.yaml](./memory.yaml)\n")
        f.write("- [memory.json](./memory.json)\n\n")
        f.write("## History\n")
        for h in history:
            f.write(f"- [{h}](./{h})\n")


def main():
    snapshot_path = sys.argv[1]
    target_dir = sys.argv[2]
    timestamp = sys.argv[3]
    iso_timestamp = sys.argv[4]

    sections = parse_snapshot(snapshot_path)
    write_tasks(target_dir, sections, timestamp, iso_timestamp)
    write_memory(target_dir, sections, timestamp, iso_timestamp)

    print(f"Tasks written to {target_dir}/tasks/")
    print(f"Memory written to {target_dir}/memory/")


if __name__ == '__main__':
    main()
