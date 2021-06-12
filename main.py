import time
import cv2
import numpy as np
import pyautogui
import subprocess
import os
from tensorflow.keras.models import model_from_json
from pynput import keyboard
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


json_file = open("model_trained.json", "r")
loaded_model_json = json_file.read()
json_file.close()
model = model_from_json(loaded_model_json)
model.load_weights("model.h5")
print("Done loading modules and model. Solver is ready to be used.")
running = False


def on_press(key):
    global running
    if key == keyboard.Key.enter and not running:
        running = True

        # Take a screenshot
        img = pyautogui.screenshot()
        img = np.array(img)
        img = img[:, :, ::-1]
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = img_gray.shape
        print("Finished getting puzzle image")

        # Get coord for the lower_right_border point of the puzzle
        x = round(width / 2)
        y = height - 2
        background_color_bottom = img_gray[y][x]
        while img_gray[y + 1][x] == background_color_bottom:
            y -= 1
        while img_gray[y][x + 2] != background_color_bottom:
            x += 1
        lower_right_border = [x, y]

        # Get coord for the upper_left point and background color of the top left box
        background_color_top = img_gray[0][round(width / 2)]
        while img_gray[y - 1][x] != background_color_top:
            y -= 1
        while img_gray[y][x - 1] != background_color_top:
            x -= 1
        x += 40
        y += 40
        box_color = img_gray[y][x]
        while img_gray[y - 1][x] == box_color:
            y -= 1
        while img_gray[y][x - 1] == box_color:
            x -= 1
        upper_left = [x, y]

        # Get anchor points of the puzzle (top left of grid), clicking point, and grid cell colors
        while img_gray[y + 1][x] == box_color:
            y += 1
        while img_gray[y][x + 1] == box_color:
            x += 1
        anchor_point_box = [x, y]
        x += 17
        y += 17
        cell_color1 = img_gray[y][x]
        while img_gray[y][x - 1] == cell_color1:
            x -= 1
        while img_gray[y - 1][x] == cell_color1:
            y -= 1
        anchor_point_grid = [x, y]
        while img_gray[y][x + 1] == cell_color1:
            x += 1
        while img_gray[y + 1][x] == cell_color1:
            y += 1
        click_point = [round((x + anchor_point_grid[0]) / 2), round((y + anchor_point_grid[1]) / 2)]
        cell_color2 = img_gray[y + 15][x + 15]

        # Get coord for the lower_right point
        x = lower_right_border[0]
        y = lower_right_border[1]
        while img_gray[y][x] != cell_color1 and img_gray[y][x] != cell_color2:
            x -= 1
            y -= 1
        lower_right = [x, y]

        # Get puzzle size and the maximum number of clues in a column/row
        puzzle_size = 0
        white_spaces = 0
        x = anchor_point_grid[0]
        y = anchor_point_grid[1]
        while img_gray[y][x] != 0:
            while img_gray[y][x] == cell_color1 or img_gray[y][x] == cell_color2:
                white_spaces += 1
                x += 1
            while img_gray[y][x] != cell_color1 and img_gray[y][x] != cell_color2 and img_gray[y][x] != 0:
                x += 1
            puzzle_size += 1
        white_spaces += puzzle_size
        clue_side_length = white_spaces / puzzle_size
        column_height = anchor_point_box[1] - upper_left[1] + 1
        clues_in_column = round(column_height / clue_side_length)
        row_width = anchor_point_box[0] - upper_left[0] + 1
        clues_in_row = round(row_width / clue_side_length)

        # Get an array of images for all of the column clues and row clues
        images = []
        x = anchor_point_grid[0]
        y = anchor_point_grid[1]
        while img_gray[y][x] != 0:
            start_x = x
            while img_gray[y][x] == cell_color1 or img_gray[y][x] == cell_color2:
                x += 1
            for i in range(0, clues_in_column):
                start_y = round(upper_left[1] + i * (column_height / clues_in_column))
                end_x = x
                end_y = round(upper_left[1] + (i + 1) * (column_height / clues_in_column))
                clue_img = img_gray[start_y:end_y, start_x:end_x]
                images.append(clue_img)
            while img_gray[y][x] != cell_color1 and img_gray[y][x] != cell_color2 and img_gray[y][x] != 0:
                x += 1
        x = anchor_point_grid[0]
        y = anchor_point_grid[1]
        while img_gray[y][x] != 0:
            start_y = y
            while img_gray[y][x] == cell_color1 or img_gray[y][x] == cell_color2:
                y += 1
            for i in range(0, clues_in_row):
                start_x = round(upper_left[0] + i * (row_width / clues_in_row))
                end_y = y
                end_x = round(upper_left[0] + (i + 1) * (row_width / clues_in_row))
                clue_img = img_gray[start_y:end_y, start_x:end_x]
                images.append(clue_img)
            while img_gray[y][x] != cell_color1 and img_gray[y][x] != cell_color2 and img_gray[y][x] != 0:
                y += 1
        print("Finished registering image")

        # Preprocess clue images
        for i in range(0, len(images)):
            images[i] = cv2.resize(images[i], (20, 20), interpolation=cv2.INTER_AREA)
            thresh, images[i] = cv2.threshold(images[i], min(cell_color1, cell_color2) - 20, 255, cv2.THRESH_BINARY)
            images[i] = cv2.equalizeHist(images[i])
        print("Finished pre-processing clue images")

        # Turn row_images and column_images into arrays of ints using machine learning model
        def predict_clue_class(input_img):
            input_img = input_img / 255
            reshaped = input_img.reshape(1, 20, 20, 1)
            # if the model isn't completely sure, it's probably looking at a col/row with just a zero
            if np.amax(model.predict(reshaped)) < 0.999:
                return 0
            return int(model.predict_classes(reshaped))

        clues = []
        zeros = np.full((20, 5), 255)
        for i in images:
            # check if blank space or 2-digit number
            num_black_pixels = 0
            left_column_hit = -1
            right_column_hit = -1
            for c in range(0, 20):
                for r in range(0, 20):
                    if i[r][c] == 0:
                        left_column_hit = c if (left_column_hit == -1 and c != 0) else left_column_hit
                        num_black_pixels += 1
                    if i[r][19 - c] == 0:
                        right_column_hit = 19 - c if (right_column_hit == -1 and c != 0) else right_column_hit

            # if square is blank
            if num_black_pixels < 10:
                clues.append(-1)
                continue

            # if square is two digits
            if right_column_hit - left_column_hit > 15:
                left_img = i[0:20, 0:10]
                left_img = np.hstack((zeros, left_img, zeros))
                right_img = i[0:20, 10:20]
                right_img = np.hstack((zeros, right_img, zeros))
                two_digit_num = 10 * predict_clue_class(left_img) + predict_clue_class(right_img)
                clues.append(two_digit_num)
                continue

            # append single digit to clues
            clues.append(predict_clue_class(i))

        print("Finished predicting clue images")

        # Write clue array to a .json file and call solver
        f = open("input.json", "w")
        f.write("{\n  \"columns\": [\n")
        for i in range(0, 2 * puzzle_size):
            len_clue_arr = clues_in_column if i < puzzle_size else clues_in_row
            clue_diff = 0 if i < puzzle_size else puzzle_size * (clues_in_column - clues_in_row)
            f.write("    [")
            for j in range(0, len_clue_arr):
                clue = clues[clue_diff + i * len_clue_arr + j]
                if clue == -1 and j == len_clue_arr - 1:
                    f.write("0")
                    break
                elif clue == -1:
                    continue
                else:
                    f.write(str(clue))
                    if j != len_clue_arr - 1:
                        f.write(", ")
            f.write("]")
            if i != puzzle_size - 1 and i != 2 * puzzle_size - 1:
                f.write(",")
            f.write("\n")
            if i == puzzle_size - 1:
                f.write("  ],\n  \"rows\": [\n")
        f.write("  ]\n}")
        f.close()
        subprocess.run(["npx", "nonogram-solver", "input.json"],
                       shell=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        os.remove("input.json")
        print("Finished solving puzzle")

        # Get array of hits and misses from solver's output file
        f = open("output/input.svg", "r")
        lines = f.readlines()
        last_line = lines[-1]
        marks = []
        for i in range(0, len(last_line) - 1):
            mark = last_line[i:(i + 2)]
            if mark == "#h":
                marks.append(True)
                i += 50
            elif mark == "#m":
                marks.append(False)
                i += 50
        f.close()
        os.remove("output/input.svg")
        os.rmdir("output")

        # Using puzzle values and marks, automatically fill in the puzzle
        pixel_width = (lower_right[0] - anchor_point_grid[0]) / puzzle_size
        x = click_point[0]
        y = click_point[1]
        for r in range(0, puzzle_size):
            for c in range(0, puzzle_size):
                if marks[r * puzzle_size + c]:
                    pyautogui.moveTo(x, y, _pause=False)
                    pyautogui.mouseDown(_pause=False)
                    time.sleep(0.023)
                    pyautogui.mouseUp(_pause=False)
                x += pixel_width
            x = click_point[0]
            y += pixel_width
        print("Done!")

        running = False


with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
