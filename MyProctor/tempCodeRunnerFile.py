import csv

with open('students.csv', mode='r') as file:
    reader = csv.reader(file)
    for row in reader:
        print(row)
