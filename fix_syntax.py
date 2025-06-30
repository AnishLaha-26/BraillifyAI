import re

def fix_braille_formatting_section():
    """Fix the syntax error in the services.py file"""
    
    # Read the file
    with open('/Users/anishlaha/Documents/GitHub/BraillifyAI/app/services.py', 'r') as f:
        content = f.read()
    
    # Find the problematic section and replace it
    old_section = '''        # Ensure consistent spacing between sections
        result = []
        for i, line in enumerate(wrapped_lines):
            result.append(line)
            # Add blank line after titles and before new sections
            if (i < len(wrapped_lines) - 1 and 
                (line.isupper() or 
                 (line.strip() and not wrapped_lines[i+1].strip()) or
                 (bool(re.match(r'^\s*[A-Z][^.!?]*$', line)) and 
                  i < len(wrapped_lines) - 1 and 
                  not wrapped_lines[i+1].startswith('  ') and 
                  not wrapped_lines[i+1].startswith(('-', '*', '•', '‣', '⁃')))):
                result.append('')
        
        return '\\n'.join(result).strip()'''
    
    new_section = '''        # Ensure consistent spacing between sections
        result = []
        for i, line in enumerate(wrapped_lines):
            result.append(line)
            # Add blank line after titles and before new sections
            if i < len(wrapped_lines) - 1:
                is_title = line.isupper()
                is_section_break = line.strip() and not wrapped_lines[i+1].strip()
                is_header = bool(re.match(r'^\s*[A-Z][^.!?]*$', line))
                
                if (is_title or is_section_break or 
                    (is_header and not wrapped_lines[i+1].startswith('  ') and 
                     not wrapped_lines[i+1].startswith(('-', '*', '•', '‣', '⁃')))):
                    result.append('')
        
        return '\\n'.join(result).strip()'''
    
    # Replace the problematic section
    if old_section in content:
        content = content.replace(old_section, new_section)
        
        # Write back to file
        with open('/Users/anishlaha/Documents/GitHub/BraillifyAI/app/services.py', 'w') as f:
            f.write(content)
        
        print("Fixed syntax error in services.py")
    else:
        print("Could not find the exact section to replace")

if __name__ == '__main__':
    fix_braille_formatting_section()
