import os
import sqlite3
from datetime import datetime

def sanitize_filename(filename):
    """
    Replace characters that are not alphanumeric or allowed punctuation with underscores.
    Allowed characters are letters, digits, dot, underscore, and hyphen.
    """
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)

def main():
    # Define paths
    db_path = 'cache.db'
    output_dir = 'exported_summaries'
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query all data from the summaries table
    cursor.execute("SELECT summary_type, keyword, summary, timestamp FROM summaries")
    rows = cursor.fetchall()
    
    if not rows:
        print("No summaries found in the database.")
        return

    for summary_type, keyword, summary, timestamp_str in rows:
        # Sanitize the keyword and timestamp to use in the file name
        sanitized_keyword = sanitize_filename(keyword)
        # Replace colons (:) in the timestamp since they are not allowed in filenames on some OSes
        sanitized_timestamp = timestamp_str.replace(":", "-")
        
        # Create a filename based on the summary_type, keyword, and timestamp
        filename = f"{summary_type}_{sanitized_keyword}_{sanitized_timestamp}.txt"
        file_path = os.path.join(output_dir, filename)
        
        # Write the summary and metadata to the text file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Summary Type: {summary_type}\n")
            f.write(f"Keyword: {keyword}\n")
            f.write(f"Timestamp: {timestamp_str}\n")
            f.write("\n")
            f.write(summary)
        
        print(f"Exported summary to: {file_path}")
    
    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
