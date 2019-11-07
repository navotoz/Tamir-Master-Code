import csv
import tkFileDialog
import json


def save_csv(data, file_name):
    """Save to csv format"""
    with open(file_name + ".csv", 'ab') as name:
        writer = csv.writer(name, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(data)


def read_csv(file_name):
    with open(file_name + ".csv", 'r') as _filehandler:
        csv_file_reader = csv.reader(_filehandler)
        data = []
        empty = True
        for row in csv_file_reader:
            while "" in row:
                row.remove("")
            if len(row) > 0:
                if len(row) == 1:
                    row = row[0].split(",")
                data.append(row)
                empty = False
            else:
                if not empty:
                    data = []
                empty = True
        return data


def save_json(name="data_file", data=None):
    with open(name + ".json", "a") as write_file:
        json.dump(data, write_file, indent=2)


def load_json(name="data_file"):
    with open(name + ".json", "r") as read_file:
        return json.load(read_file)


def fix_json(file_name):
    with open(file_name + ".json", 'r') as filehandler:
        file_reader = filehandler.readlines()
        data = []
        empty = True
        for row in file_reader:
            if len(row) > 0:
                if '][' in row:
                    row = ',\n'
                data.append(row)
                empty = False
            else:
                if not empty:
                    data = []
                empty = True
    with open(file_name + "_fixed.json", 'w') as name:
        name.writelines(data)


if __name__ == '__main__':
    files = tkFileDialog.askopenfilenames(filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
    new_file_name = "results" + files[0][-13:-5]
    for i in range(len(files)):
        save_csv(read_csv(files[i][:-4]), new_file_name)
        fix_json(files[i][:-4])
        save_json(data=load_json(files[i][:-4] + "_fixed"), name=new_file_name)