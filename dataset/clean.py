import csv
import sys

def remove_eleventh_column(input_file_path, output_file_path):
    with open(input_file_path, 'r', newline='') as infile, open(output_file_path, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Skip the header (first line) and write it as is
        header = next(reader)
        writer.writerow(header)

        # Process each row starting from the second line
        for row in reader:
            # Ensure that if there are more than 10 columns, only keep up to the 10th
            if len(row) > 10:
                row = row[:10]
            writer.writerow(row)

# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: script.py <input_file.csv> <output_file.csv>")
        sys.exit(1)

    input_file_path = sys.argv[1]
    output_file_path = sys.argv[2]
    remove_eleventh_column(input_file_path, output_file_path)
