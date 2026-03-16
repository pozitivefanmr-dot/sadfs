import os

path = os.path.join(os.path.dirname(__file__), 'casino', 'templates', 'base.html')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Find the line with "const msgClass" and add prefixHtml variable before "html +="
old = "const msgClass = msg.is_me ? 'msg-me' : 'msg-other';"
idx = text.index(old)
# Find the next "html += `" after this point
html_idx = text.index("html += `", idx)
# Insert prefixHtml declaration between msgClass line and html +=
insert_text = """
                        // Prefix tag
                        const prefixHtml = msg.prefix
                            ? `<span class="chat-tag" style="color: ${msg.prefix_color}">(${escapeHtml(msg.prefix)})</span>`
                            : '';

                        """
# Find the content between end of msgClass line and html +=
between_start = idx + len(old)
# Replace the gap
text = text[:between_start] + insert_text + text[html_idx:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Done!")
