# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/a_warnings.ipynb.

# %% auto 0
__all__ = ['custom_warning_format', 'custom_warning']

# %% ../nbs/a_warnings.ipynb 2
import warnings
import textwrap

# %% ../nbs/a_warnings.ipynb 3
# Custom warning format function with line wrapping and indentation
def custom_warning_format(message, category, filename, lineno, line=None):
    formatted_message = textwrap.fill(message, width=100, initial_indent='  ', subsequent_indent='  ')
    return f"{filename}:{lineno}: {category.__name__}:\n{formatted_message}\n"

# Custom warning handler
def custom_warning(message, category, filename, lineno, file=None, line=None):
    formatted_message = custom_warning_format(str(message), category, filename, lineno)
    print(formatted_message)

warnings.showwarning = custom_warning
warnings.filterwarnings("always")
