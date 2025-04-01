import re
from functools import partial
from typing import Callable, List, Pattern, Tuple, Union

def find_all_index(text: str, pattern: str) -> List[int]:
    """Find all start and end indices of matches in the text.
    
    Args:
        text: The string to search in
        pattern: Regular expression pattern with a capturing group
        
    Returns:
        List of indices including start and end of the string
    """
    index_list = [0]
    for match in re.finditer(pattern, text, re.MULTILINE):
        if match.group(1) is not None:
            index_list.extend([match.start(1), match.end(1)])
    index_list.append(len(text))
    return index_list

def replace_all(text: str, pattern: str, function: Callable[[str], str]) -> str:
    """Replace all matches of a pattern with the result of a function.
    
    Args:
        text: The string to modify
        pattern: Regular expression pattern
        function: Function that takes a matched string and returns a replacement
        
    Returns:
        Modified string with replacements
    """
    poslist = find_all_index(text, pattern)
    strlist = []
    originstr = []
    
    # Extract matched parts and transform them
    for i in range(1, len(poslist) - 1, 2):
        start, end = poslist[i:i+2]
        strlist.append(function(text[start:end]))
    
    # Extract non-matched parts
    for i in range(0, len(poslist), 2):
        if i + 1 < len(poslist):
            j, k = poslist[i:i+2]
            originstr.append(text[j:k])
    
    # Handle edge cases with list lengths
    if len(strlist) < len(originstr):
        strlist.append('')
    else:
        originstr.append('')
    
    # Interleave the original and transformed parts
    new_list = [item for pair in zip(originstr, strlist) for item in pair]
    return ''.join(new_list)

# Escape functions for different contexts
def escapeshape(text: str) -> str:
    """Format heading text."""
    return '▎*' + " ".join(text.split()[1:]) + '*\n\n'

def escapeminus(text: str) -> str:
    """Escape minus characters."""
    return '\\' + text

def escapeminus2(text: str) -> str:
    """Placeholder for minus characters in code blocks."""
    return r'@+>@'

def escapebackquote(text: str) -> str:
    """Escape back quotes."""
    return r'\`\`'

def escapebackquoteincode(text: str) -> str:
    """Placeholder for back quotes in code blocks."""
    return r'@->@'

def escapeplus(text: str) -> str:
    """Escape plus characters."""
    return '\\' + text

def escape_all_backquote(text: str) -> str:
    """Escape all back quotes."""
    return '\\' + text

def find_lines_with_unbalanced_chars(text: str, char: str) -> str:
    """
    Find lines with unbalanced occurrences of a character and escape them.
    
    Args:
        text: The text to process
        char: The character to check for balance
        
    Returns:
        Processed text with escaped characters where needed
    """
    lines = text.split('\n')
    
    for index, line in enumerate(lines):
        # Skip checking inside code blocks
        cleaned_line = re.sub(r"```", '', line)
        # Check if character count is odd or if it's not a code block start and has odd char count
        if (cleaned_line.count(char) % 2 != 0 or 
            (not line.strip().startswith("```") and line.count(char) % 2 != 0)):
            lines[index] = replace_all(lines[index], r"\\`|(`)", escape_all_backquote)
    
    return "\n".join(lines)

def escape(text: str, preserve_double_backslash: bool = 0) -> str:
    """
    Escape Markdown special characters in text.
    
    Args:
        text: The text to escape
        preserve_double_backslash: Flag to preserve double backslashes
        
    Returns:
        Escaped text safe for Markdown
    """
    # Preserve certain escaped brackets temporarily
    text = re.sub(r"\\\[", '@->@', text)
    text = re.sub(r"\\\]", '@<-@', text)
    text = re.sub(r"\\\(", '@-->@', text)
    text = re.sub(r"\\\)", '@<--@', text)
    
    # Handle double backslashes if needed
    if preserve_double_backslash:
        text = re.sub(r"\\\\", '@@@', text)
    
    # Preserve escaped backticks
    text = re.sub(r"\\`", '@<@', text)
    
    # Double all backslashes
    text = re.sub(r"\\", r"\\\\", text)
    
    # Restore double backslashes if needed
    if preserve_double_backslash:
        text = re.sub(r"\@{3}", r"\\\\", text)
    
    # Escape Markdown special characters
    text = re.sub(r"_", '\_', text)
    
    # Preserve bold text
    text = re.sub(r"\*{2}(.*?)\*{2}", '@@@\\1@@@', text)
    
    # Convert asterisk lists to bullet points
    text = re.sub(r"\n{1,2}\*\s", '\n\n• ', text)
    
    # Escape single asterisks
    text = re.sub(r"\*", '\*', text)
    
    # Restore bold text
    text = re.sub(r"\@{3}(.*?)\@{3}", '*\\1*', text)
    
    # Handle links
    text = re.sub(r"\!?\[(.*?)\]\((.*?)\)", '@@@\\1@@@^^^\\2^^^', text)
    
    # Escape brackets and parentheses
    text = re.sub(r"\[", '\[', text)
    text = re.sub(r"\]", '\]', text)
    text = re.sub(r"\(", '\(', text)
    text = re.sub(r"\)", '\)', text)
    
    # Restore preserved brackets
    text = re.sub(r"\@\-\>\@", '\[', text)
    text = re.sub(r"\@\<\-\@", '\]', text)
    text = re.sub(r"\@\-\-\>\@", '\(', text)
    text = re.sub(r"\@\<\-\-\@", '\)', text)
    
    # Restore links
    text = re.sub(r"\@{3}(.*?)\@{3}\^{3}(.*?)\^{3}", '[\\1](\\2)', text)
    
    # Escape more special characters
    text = re.sub(r"~", '\~', text)
    text = re.sub(r">", '\>', text)
    
    # Handle headings
    text = replace_all(text, r"(^#+\s.+?\n+)|```[\D\d\s]+?```", escapeshape)
    text = re.sub(r"#", '\#', text)
    
    # Handle plus signs and list items
    text = replace_all(text, r"(\+)|\n[\s]*-\s|```[\D\d\s]+?```|`[\D\d\s]*?`", escapeplus)
    
    # Format numbered lists
    text = re.sub(r"\n{1,2}(\s*\d{1,2}\.\s)", '\n\n\\1', text)
    
    # Handle minus signs inside and outside code blocks
    text = replace_all(text, r"```[\D\d\s]+?```|(-)", escapeminus2)
    text = re.sub(r"-", '@<+@', text)
    text = re.sub(r"\@\+\>\@", '-', text)
    
    # Convert minus lists to bullet points
    text = re.sub(r"\n{1,2}(\s*)-\s", '\n\n\\1• ', text)
    text = re.sub(r"\@\<\+\@", '\-', text)
    text = replace_all(text, r"(-)|\n[\s]*-\s|```[\D\d\s]+?```|`[\D\d\s]*?`", escapeminus)
    
    # Preserve code blocks
    text = re.sub(r"```([\D\d\s]+?)```", '@@@\\1@@@', text)
    
    # Handle backticks in code blocks
    text = replace_all(text, r"\@\@\@[\s\d\D]+?\@\@\@|(`)", escapebackquoteincode)
    text = re.sub(r"`", '\`', text)
    text = re.sub(r"\@\<\@", '\`', text)
    text = re.sub(r"\@\-\>\@", '`', text)
    
    # Handle double backticks
    text = replace_all(text, r"(``)", escapebackquote)
    
    # Restore code blocks
    text = re.sub(r"\@{3}([\D\d\s]+?)\@{3}", '```\\1```', text)
    
    # Escape remaining special characters
    text = re.sub(r"=", '\=', text)
    text = re.sub(r"\|", '\|', text)
    text = re.sub(r"{", '\{', text)
    text = re.sub(r"}", '\}', text)
    text = re.sub(r"\.", '\.', text)
    text = re.sub(r"!", '\!', text)
    
    # Handle lines with unbalanced backticks
    text = find_lines_with_unbalanced_chars(text, '`')
    
    return text

def beautify_views(views: str) -> str:
    """
    Format view counts with appropriate suffixes (k, m, b).
    
    Args:
        views: String containing a number of views
        
    Returns:
        Formatted view count with appropriate suffix
    """
    # Extract only digits from the input
    views = ''.join(filter(str.isdigit, views))
    
    # Convert to integer
    views_int = int(views)
    
    # Format based on magnitude
    if views_int < 1000:
        return str(views_int)
    elif views_int < 1_000_000:
        return f"{views_int / 1000:.1f} <b>k</b>"
    elif views_int < 1_000_000_000:
        return f"{views_int / 1_000_000:.1f} <b>m</b>"
    else:
        return f"{views_int / 1_000_000_000:.1f} <b>b</b>"


if __name__ == '__main__':
    import os
    os.system('clear')
    text = escape(input("text"))
    print(text)