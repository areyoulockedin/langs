import yaml
import os
import argparse
from collections import defaultdict # Useful for grouping extensions by language

# --- Configuration ---
DEFAULT_YAML_FILE = 'languages.yml'
DEFAULT_LANG_TYPE_OUTPUT_FILE = 'gen/lang.d.ts' # Example paths
DEFAULT_EXTENSION_MAP_OUTPUT_FILE = 'gen/extension-map.ts' # Example paths
DEFAULT_MARKDOWN_OUTPUT_FILE = './README.md' # Markdown output file
# Assuming FileType is defined in this path relative to extensionMap.ts
# Adjust if your 'FileType' lives elsewhere or if you want to use the generated 'Language' type
FILE_TYPE_IMPORT_PATH = "@/types/lang"
# --- End Configuration ---

def sanitize_string_for_ts(input_string):
  """Escapes characters potentially problematic in TS string literals."""
  return input_string.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`')

def generate_files(yaml_file_path, lang_output_path, map_output_path, md_output_path):
    """
    Reads the YAML file and generates the TypeScript and Markdown files.
    """
    print(f"Reading YAML file: {yaml_file_path}")
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            languages_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: YAML file not found at '{yaml_file_path}'")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return

    if not isinstance(languages_data, dict):
        print("Error: YAML content does not seem to be a valid dictionary (map).")
        print("Expected format: LanguageName: { details... }")
        return

    language_names = []
    extension_map = {}
    # Store extensions per language for Markdown generation
    language_to_extensions_md = defaultdict(list)

    print("Processing language data...")
    # Sort language names primarily for deterministic output
    sorted_language_keys = sorted(languages_data.keys())

    for lang_name in sorted_language_keys:
        lang_details = languages_data[lang_name]
        sanitized_lang_name = sanitize_string_for_ts(lang_name)
        language_names.append(sanitized_lang_name)

        # Check if 'extensions' field exists and is a list
        if isinstance(lang_details, dict) and 'extensions' in lang_details and isinstance(lang_details['extensions'], list):
            valid_extensions = []
            for ext in lang_details['extensions']:
                if isinstance(ext, str) and ext.startswith('.'):
                    # Keep original extension format (with dot) for Markdown
                    language_to_extensions_md[sanitized_lang_name].append(ext)

                    # Normalize for TS map: lowercase and remove leading dot
                    normalized_ext = ext[1:].lower()
                    if normalized_ext: # Avoid empty strings if extension was just "."
                        # Store the *original* (but sanitized) language name from the YAML key
                        extension_map[normalized_ext] = sanitized_lang_name


    # Sort extension map by extension for consistent TS output
    sorted_extension_items = sorted(extension_map.items())

    # --- Generate languages.ts (Type Union) ---
    print(f"Generating TypeScript Language type file: {lang_output_path}")
    try:
        os.makedirs(os.path.dirname(lang_output_path), exist_ok=True) # Ensure directory exists
        with open(lang_output_path, 'w', encoding='utf-8') as f:
            f.write("/**\n * Defines all language names derived from the source YAML.\n */\n")
            f.write("export type FileType=\n")
            if language_names:
                # Sort names for the type definition itself for consistency
                language_names.sort()
                f.write(f'  | "{language_names[0]}"\n') # First item
                for name in language_names[1:]:
                    f.write(f'  | "{name}"\n')
            else:
                f.write("  | never; // No languages found in YAML\n")
            # f.write(";\n") # Optional semicolon
    except IOError as e:
        print(f"Error writing to Language type file '{lang_output_path}': {e}")
        # Continue to generate other files if possible
    except Exception as e:
        print(f"An unexpected error occurred while writing the Language type file: {e}")

    # --- Generate extensionMap.ts (Mapping) ---
    print(f"Generating TypeScript extension map file: {map_output_path}")
    try:
        os.makedirs(os.path.dirname(map_output_path), exist_ok=True) # Ensure directory exists
        with open(map_output_path, 'w', encoding='utf-8') as f:
            f.write(f'import type {{ FileType }} from "{FILE_TYPE_IMPORT_PATH}";\n\n')
            f.write("/**\n * Maps lowercase file extensions (without leading dot) to their corresponding language name.\n")
            f.write(" * Generated from the source YAML file.\n */\n")
            f.write("export const fileExtensionMap: Record<string, FileType> = {\n")
            for ext, lang in sorted_extension_items:
                 f.write(f'  "{ext}": "{lang}",\n')
            f.write("};\n")
    except IOError as e:
        print(f"Error writing to extension map file '{map_output_path}': {e}")
         # Continue to generate other files if possible
    except Exception as e:
         print(f"An unexpected error occurred while writing the extension map file: {e}")

    # --- Generate Markdown File ---
    print(f"Generating Markdown extensions file: {md_output_path}")
    try:
        os.makedirs(os.path.dirname(md_output_path), exist_ok=True) # Ensure directory exists
        with open(md_output_path, 'w', encoding='utf-8') as f:
            f.write("# areyoulocked.in - Supported File Types\n\n")
            f.write("This file lists programming languages and their associated file extensions, generated from the source YAML.\n\n")

            # Iterate through sorted language names for consistent MD output
            # Using the already sorted 'sorted_language_keys' list
            for lang_name in sorted_language_keys:
                f.write(f"## {lang_name}\n\n")
                extensions = language_to_extensions_md.get(lang_name) # Use .get() for safety
                if extensions:
                    # Format extensions using inline code blocks
                    formatted_extensions = ", ".join(f"`{ext}`" for ext in extensions)
                    f.write(f"Extensions: {formatted_extensions}\n\n")
                else:
                    f.write("Extensions: *(None listed)*\n\n")

    except IOError as e:
        print(f"Error writing to Markdown file '{md_output_path}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred while writing the Markdown file: {e}")


    print("\nFile generation process complete!")
    print(f" - Language types written to: {lang_output_path}")
    print(f" - Extension map written to: {map_output_path}")
    print(f" - Markdown extensions written to: {md_output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate TypeScript types, extension map, and Markdown documentation from a language YAML file.')
    parser.add_argument(
        '-i', '--input',
        default=DEFAULT_YAML_FILE,
        help=f'Path to the input YAML file (default: {DEFAULT_YAML_FILE})'
    )
    parser.add_argument(
        '-t', '--type-output',
        default=DEFAULT_LANG_TYPE_OUTPUT_FILE,
        help=f'Path for the output TS Language type file (default: {DEFAULT_LANG_TYPE_OUTPUT_FILE})'
    )
    parser.add_argument(
        '-m', '--map-output',
        default=DEFAULT_EXTENSION_MAP_OUTPUT_FILE,
        help=f'Path for the output TS extension map file (default: {DEFAULT_EXTENSION_MAP_OUTPUT_FILE})'
    )
    parser.add_argument(
        '-d', '--md-output', # Changed from '--markdown-output' for brevity
        default=DEFAULT_MARKDOWN_OUTPUT_FILE,
        help=f'Path for the output Markdown extensions file (default: {DEFAULT_MARKDOWN_OUTPUT_FILE})'
    )

    args = parser.parse_args()

    # Ensure output directories exist before calling generate_files
    # (Though generate_files now also does this for robustness)
    for output_path in [args.type_output, args.map_output, args.md_output]:
        output_dir = os.path.dirname(output_path)
        if output_dir: # Only create if path includes a directory
             os.makedirs(output_dir, exist_ok=True)


    generate_files(args.input, args.type_output, args.map_output, args.md_output)
