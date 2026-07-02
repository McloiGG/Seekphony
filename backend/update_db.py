import sqlite3

# Connect to your SQLite database file
conn = sqlite3.connect('data/seekphony.sqlite3')

# UPDATE THIS LINE: Use your exact folder name with the space intact!
conn.execute("UPDATE songs SET file_path = 'data/Music list/Ed Sheeran  Shape of You.mp3' WHERE id = 2")
conn.execute("UPDATE songs SET file_path = 'data/Music list/Billie Eilish - bad guy.mp3' WHERE id = 3")
# Save the changes
conn.commit()

print('🚀 Verification: Path saved permanently with the correct folder name!')