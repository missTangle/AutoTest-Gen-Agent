#!/usr/bin/env python3
"""
md_to_xmind.py - Convert Markdown test cases to XMind format
Usage: python md_to_xmind.py <input.md> [output.xmind]
"""

import sys
import re
import os
import xmind

def parse_markdown_to_tree(md_content):
    """
    Parse markdown content into a tree structure.
    Returns: list of tuples (level, title, content_lines)
    level: 0 for root, 1 for #, 2 for ##, 3 for ###, etc.
    """
    lines = md_content.split('\n')
    tree = []
    current_section = []
    
    for line in lines:
        # Check for headings
        match = re.match(r'^(#+)\s+(.+)$', line.strip())
        if match:
            # Save previous section if exists
            if current_section:
                tree.append(current_section)
                current_section = []
            
            level = len(match.group(1))  # # count
            title = match.group(2).strip()
            current_section = [level, title, []]
        elif current_section:
            # Add content line to current section
            if line.strip() and not line.strip().startswith('---'):
                current_section[2].append(line.rstrip())
    
    # Add the last section
    if current_section:
        tree.append(current_section)
    
    return tree

def add_topic(parent_topic, level, title, content_lines):
    """Add a topic to parent with given level and title"""
    topic = parent_topic.addSubTopic()
    topic.setTitle(title)
    
    # Add content lines as notes or subtopics
    if content_lines:
        # Filter out empty lines and markdown list markers
        filtered_lines = []
        for line in content_lines:
            if line.strip() and not line.strip().startswith('---'):
                # Clean up markdown formatting
                clean_line = re.sub(r'^\s*[-*]\s*', '', line)
                clean_line = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_line)
                filtered_lines.append(clean_line.strip())
        
        if filtered_lines:
            # Join lines for note
            note_text = '\n'.join(filtered_lines)
            topic.setPlainNotes(note_text)
    
    return topic

def build_xmind_from_tree(tree, workbook):
    """Build XMind structure from parsed tree"""
    sheet = workbook.getPrimarySheet()
    sheet.setTitle("Test Cases")
    root_topic = sheet.getRootTopic()
    root_topic.setTitle("Network & Internet Test Cases")
    
    # Organize by level
    stack = [(0, root_topic)]  # (level, parent_topic)
    
    for level, title, content_lines in tree:
        # Find appropriate parent
        while stack and stack[-1][0] >= level:
            stack.pop()
        
        if not stack:
            # Should not happen
            continue
        
        _, parent = stack[-1]
        topic = add_topic(parent, level, title, content_lines)
        stack.append((level, topic))
    
    return workbook

def main():
    if len(sys.argv) < 2:
        print("Usage: python md_to_xmind.py <input.md> [output.xmind]")
        print("Example: python md_to_xmind.py Network_Test.md Network_Test.xmind")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        # Default output name
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.xmind"
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    print(f"Reading Markdown from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print("Parsing Markdown structure...")
    tree = parse_markdown_to_tree(md_content)
    print(f"Found {len(tree)} top-level sections")
    
    print("Creating XMind workbook...")
    # xmind.load will create a new workbook if file doesn't exist
    workbook = xmind.load(output_file)
    
    workbook = build_xmind_from_tree(tree, workbook)
    
    print(f"Saving XMind file to: {output_file}")
    xmind.save(workbook, output_file)
    
    print(f"Successfully converted '{input_file}' to '{output_file}'")
    print(f"Output file: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    main()