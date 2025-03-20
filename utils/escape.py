import re

def find_all_index(text, pattern):
    """Find all starting and ending indices of matches for a regex pattern.
    
    Args:
        text: The string to search in
        pattern: The regex pattern with capturing group
        
    Returns:
        A list of indices marking the boundaries of matches and non-matches
    """
    index_list = [0]
    for match in re.finditer(pattern, text, re.MULTILINE):
        if match.group(1) is not None:
            start = match.start(1)
            end = match.end(1)
            index_list += [start, end]
    index_list.append(len(text))
    return index_list

def replace_all(text, pattern, function):
    """Replace all matches of a pattern with the result of a function.
    
    Args:
        text: The string to perform replacements on
        pattern: The regex pattern with capturing group
        function: A function that takes a match string and returns a replacement
        
    Returns:
        The text with all replacements applied
    """
    poslist = find_all_index(text, pattern)
    
    # Extract parts that match the pattern (to be transformed)
    matched_parts = []
    for i in range(1, len(poslist) - 1, 2):
        start, end = poslist[i], poslist[i + 1]
        matched_parts.append(function(text[start:end]))
    
    # Extract parts that don't match the pattern (to be preserved)
    preserved_parts = []
    for i in range(0, len(poslist), 2):
        if i + 1 < len(poslist):
            j, k = poslist[i], poslist[i + 1]
            preserved_parts.append(text[j:k])
    
    # Handle edge cases with different list lengths
    if len(matched_parts) < len(preserved_parts):
        matched_parts.append('')
    elif len(preserved_parts) < len(matched_parts):
        preserved_parts.append('')
    
    # Interleave the preserved and transformed parts
    result = []
    for orig, transformed in zip(preserved_parts, matched_parts):
        result.append(orig)
        result.append(transformed)
    
    return ''.join(result)

def escapeshape(text):
    """Format headers for Telegram markdown.
    
    Args:
        text: Header text
        
    Returns:
        Formatted header for Telegram
    """
    if not text.strip():
        return ''
    
    # Extract header text without the # marks
    words = text.split()
    if words and words[0].startswith('#'):
        return '▎*' + " ".join(words[1:]) + '*\n\n'
    return text

def escape_special_char(text):
    """Escape a special character by adding backslash.
    
    Args:
        text: The character to escape
        
    Returns:
        Escaped character
    """
    return '\\' + text

def escape_minus(text):
    """Escape minus character.
    
    Args:
        text: Text containing minus
        
    Returns:
        Text with escaped minus
    """
    return '\\' + text

def escape_temp_minus(text):
    """Convert minus to temporary marker.
    
    Args:
        text: Text containing minus
        
    Returns:
        Text with minus replaced by marker
    """
    return r'@+>@'

def escape_backquote(text):
    """Escape double backticks.
    
    Args:
        text: Text containing backticks
        
    Returns:
        Text with escaped backticks
    """
    return r'\`\`'

def escape_backquote_in_code(text):
    """Replace backtick in code blocks with temporary marker.
    
    Args:
        text: Text containing backtick
        
    Returns:
        Text with backtick replaced by marker
    """
    return r'@->@'

def fix_uneven_backticks(text):
    """Fix lines with uneven backtick counts.
    
    Args:
        text: The text to process
        
    Returns:
        Text with properly escaped backticks
    """
    lines = text.split('\n')
    in_code_block = False
    
    for index, line in enumerate(lines):
        # Skip backtick escaping within code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
            
        # Only process lines not in code blocks
        if not in_code_block:
            # Count backticks outside of existing escaped sequences
            clean_line = re.sub(r"\\`", '', line)
            if clean_line.count('`') % 2 != 0:
                # Replace all unescaped backticks with escaped ones
                lines[index] = replace_all(line, r"\\`|(`)", lambda x: '\\' + x)
    
    return "\n".join(lines)

def escape(text, flag=0):
    """Escape text to be Telegram-compatible.
    
    Args:
        text: The text to escape
        flag: Flag for special handling of backslashes
        
    Returns:
        Telegram-compatible escaped text
    """
    # Save already escaped brackets and parentheses
    text = re.sub(r"\\\[", '@->@', text)
    text = re.sub(r"\\\]", '@<-@', text)
    text = re.sub(r"\\\(", '@-->@', text)
    text = re.sub(r"\\\)", '@<--@', text)
    
    # Handle backslashes special case
    if flag:
        text = re.sub(r"\\\\", '@@@', text)
    
    # Save escaped backticks
    text = re.sub(r"\\`", '@<@', text)
    
    # Double all backslashes
    text = re.sub(r"\\", r"\\\\", text)
    
    # Restore special backslashes if needed
    if flag:
        text = re.sub(r"\@{3}", r"\\\\", text)
    
    # Escape underscores
    text = re.sub(r"_", '\_', text)
    
    # Handle bold text (save for later restoration)
    text = re.sub(r"\*{2}(.*?)\*{2}", '@@@\\1@@@', text)
    
    # Convert bullet lists
    text = re.sub(r"\n{1,2}\*\s", '\n\n• ', text)
    
    # Escape asterisks
    text = re.sub(r"\*", '\*', text)
    
    # Restore bold text
    text = re.sub(r"\@{3}(.*?)\@{3}", '*\\1*', text)
    
    # Handle links (save for later restoration)
    text = re.sub(r"\!?\[(.*?)\]\((.*?)\)", '@@@\\1@@@^^^\\2^^^', text)
    
    # Escape brackets and parentheses
    text = re.sub(r"\[", '\[', text)
    text = re.sub(r"\]", '\]', text)
    text = re.sub(r"\(", '\(', text)
    text = re.sub(r"\)", '\)', text)
    
    # Restore saved brackets and parentheses
    text = re.sub(r"\@\-\>\@", '\[', text)
    text = re.sub(r"\@\<\-\@", '\]', text)
    text = re.sub(r"\@\-\-\>\@", '\(', text)
    text = re.sub(r"\@\<\-\-\@", '\)', text)
    
    # Restore links
    text = re.sub(r"\@{3}(.*?)\@{3}\^{3}(.*?)\^{3}", '[\\1](\\2)', text)
    
    # Escape other special characters
    text = re.sub(r"~", '\~', text)
    text = re.sub(r">", '\>', text)
    
    # Format headers
    text = replace_all(text, r"(^#+\s.+?\n+)|```[\D\d\s]+?```", escapeshape)
    
    # Escape hash marks
    text = re.sub(r"#", '\#', text)
    
    # Handle plus and list items
    text = replace_all(text, r"(\+)|\n[\s]*-\s|```[\D\d\s]+?```|`[\D\d\s]*?`", escape_special_char)
    
    # Format numbered lists
    text = re.sub(r"\n{1,2}(\s*\d{1,2}\.\s)", '\n\n\\1', text)
    
    # Handle minus signs: first preserve those in code blocks
    text = replace_all(text, r"```[\D\d\s]+?```|(-)", escape_temp_minus)
    text = re.sub(r"-", '@<+@', text)
    text = re.sub(r"\@\+\>\@", '-', text)
    
    # Convert dash lists to bullet points
    text = re.sub(r"\n{1,2}(\s*)-\s", '\n\n\\1• ', text)
    
    # Escape remaining minus signs
    text = re.sub(r"\@\<\+\@", '\-', text)
    text = replace_all(text, r"(-)|\n[\s]*-\s|```[\D\d\s]+?```|`[\D\d\s]*?`", escape_minus)
    
    # Save code blocks for later restoration
    text = re.sub(r"```([\D\d\s]+?)```", '@@@\\1@@@', text)
    
    # Handle backticks in code blocks
    text = replace_all(text, r"\@\@\@[\s\d\D]+?\@\@\@|(`)", escape_backquote_in_code)
    
    # Escape remaining backticks
    text = re.sub(r"`", '\`', text)
    text = re.sub(r"\@\<\@", '\`', text)
    text = re.sub(r"\@\-\>\@", '`', text)
    
    # Handle double backticks
    text = replace_all(text, r"(``)", escape_backquote)
    
    # Restore code blocks
    text = re.sub(r"\@{3}([\D\d\s]+?)\@{3}", '```\\1```', text)
    
    # Escape remaining special characters
    text = re.sub(r"=", '\=', text)
    text = re.sub(r"\|", '\|', text)
    text = re.sub(r"{", '\{', text)
    text = re.sub(r"}", '\}', text)
    text = re.sub(r"\.", '\.', text)
    text = re.sub(r"!", '\!', text)
    
    # Fix lines with uneven backtick counts
    text = fix_uneven_backticks(text)
    
    return text

def beautify_views(views):
    """Format view counts in a readable way.
    
    Args:
        views: The view count string or number
        
    Returns:
        Formatted view count (e.g., "1.2 k", "3.4 m")
    """
    if not views:
        return "0"
        
    # Extract digits from the input
    views = ''.join(filter(str.isdigit, str(views)))
    
    if not views:
        return "0"
        
    views = int(views)
    
    if views < 1000:
        return str(views)
    elif views < 1_000_000:
        return f"{views / 1000:.1f} <b>k</b>"
    elif views < 1_000_000_000:
        return f"{views / 1_000_000:.1f} <b>m</b>"
    else:
        return f"{views / 1_000_000_000:.1f} <b>b</b>"


if __name__ == '__main__':
    import os
    # Clear terminal screen
    os.system('clear' if os.name == 'posix' else 'cls')
    
    # Get input from user and escape it
    sample_text = """
# This is a header
This is some text with *italics* and **bold** and `code`.
Here's a [link](https://example.com).

This is a list:
* Item 1
* Item 2
- Item 3
- Item 4

1. Numbered item
2. Another numbered item

```python
def hello():
    print("Hello world!")
    # Comments with # and special chars: _*[]()~`>#+-=|{}.!
```

Special characters: _*[]()~`>#+-=|{}.!
    """
    
    print("Sample text:")
    print("-" * 40)
    print(sample_text)
    print("-" * 40)
    
    escaped_text = escape(sample_text)
    print("\nEscaped text for Telegram:")
    print("-" * 40)
    print(escaped_text)
    print("-" * 40)
    
    print("\nEnter your own text to escape (or press Enter to skip):")
    user_input = input()
    if user_input:
        print("\nYour escaped text:")
        print("-" * 40)
        print(escape(user_input))