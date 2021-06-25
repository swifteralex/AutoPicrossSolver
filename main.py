import time
import cv2
import numpy as np
import pyautogui
import os
import datetime
from picross_solver import picross_solver as solver
from tensorflow.keras.models import model_from_json
from pynput import keyboard
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


#########################################################
#                   PROGRAM VARIABLES                   #

click_speed = 0.029  # Time between each click in seconds
exit_key = keyboard.Key.esc  # Key to exit the program
start_key = keyboard.Key.enter  # Key to start the solver

#########################################################


def register_image(input_img):
    # Get coord for the lower_right_border point of the puzzle
    height, width = input_img.shape
    x = round(width / 2)
    y = height - 2
    background_color_bottom = input_img[y][x]
    while input_img[y + 1][x] == background_color_bottom:
        y -= 1
    while input_img[y][x + 2] != background_color_bottom:
        x += 1
    lower_right_border = [x, y]

    # Get coord for the upper_left point and background color of the top left box
    background_color_top = input_img[0][round(width / 2)]
    while input_img[y - 1][x] != background_color_top:
        y -= 1
    while input_img[y][x - 1] != background_color_top:
        x -= 1
    x += 40
    y += 40
    box_color = input_img[y][x]
    while input_img[y - 1][x] == box_color:
        y -= 1
    while input_img[y][x - 1] == box_color:
        x -= 1
    upper_left = [x, y]

    # Get anchor points of the puzzle (top left of grid), clicking point, and grid cell colors
    while input_img[y + 1][x] == box_color:
        y += 1
    while input_img[y][x + 1] == box_color:
        x += 1
    anchor_point_box = [x, y]
    x += 17
    y += 17
    cell_color1 = input_img[y][x]
    while input_img[y][x - 1] == cell_color1:
        x -= 1
    while input_img[y - 1][x] == cell_color1:
        y -= 1
    anchor_point_grid = [x, y]
    while input_img[y][x + 1] == cell_color1:
        x += 1
    while input_img[y + 1][x] == cell_color1:
        y += 1
    click_point = [round((x + anchor_point_grid[0]) / 2), round((y + anchor_point_grid[1]) / 2)]
    cell_color2 = input_img[y + 15][x + 15]

    # Get coord for the lower_right point
    x = lower_right_border[0]
    y = lower_right_border[1]
    while input_img[y][x] != cell_color1 and input_img[y][x] != cell_color2:
        x -= 1
        y -= 1
    lower_right = [x, y]

    # Get puzzle size and the maximum number of clues in a column/row
    puzzle_size = 0
    white_spaces = 0
    x = anchor_point_grid[0]
    y = anchor_point_grid[1]
    while input_img[y][x] != 0:
        while input_img[y][x] == cell_color1 or input_img[y][x] == cell_color2:
            white_spaces += 1
            x += 1
        while input_img[y][x] != cell_color1 and input_img[y][x] != cell_color2 and input_img[y][x] != 0:
            x += 1
        puzzle_size += 1
    white_spaces += puzzle_size
    clue_side_length = white_spaces / puzzle_size
    column_height = anchor_point_box[1] - upper_left[1] + 1
    clues_in_column = round(column_height / clue_side_length)
    row_width = anchor_point_box[0] - upper_left[0] + 1
    clues_in_row = round(row_width / clue_side_length)
    pixel_width = (lower_right[0] - anchor_point_grid[0]) / puzzle_size

    # Get an array of images for all of the column clues and row clues
    images = []
    x = anchor_point_grid[0]
    y = anchor_point_grid[1]
    while input_img[y][x] != 0:
        start_x = x
        while input_img[y][x] == cell_color1 or input_img[y][x] == cell_color2:
            x += 1
        for i in range(0, clues_in_column):
            start_y = round(upper_left[1] + i * (column_height / clues_in_column))
            end_x = x
            end_y = round(upper_left[1] + (i + 1) * (column_height / clues_in_column))
            clue_img = input_img[start_y:end_y, start_x:end_x]
            images.append(clue_img)
        while input_img[y][x] != cell_color1 and input_img[y][x] != cell_color2 and input_img[y][x] != 0:
            x += 1
    x = anchor_point_grid[0]
    y = anchor_point_grid[1]
    while input_img[y][x] != 0:
        start_y = y
        while input_img[y][x] == cell_color1 or input_img[y][x] == cell_color2:
            y += 1
        for i in range(0, clues_in_row):
            start_x = round(upper_left[0] + i * (row_width / clues_in_row))
            end_y = y
            end_x = round(upper_left[0] + (i + 1) * (row_width / clues_in_row))
            clue_img = input_img[start_y:end_y, start_x:end_x]
            images.append(clue_img)
        while input_img[y][x] != cell_color1 and input_img[y][x] != cell_color2 and input_img[y][x] != 0:
            y += 1

    # Preprocess clue images
    for i in range(0, len(images)):
        images[i] = cv2.resize(images[i], (20, 20), interpolation=cv2.INTER_AREA)
        thresh, images[i] = cv2.threshold(images[i], min(cell_color1, cell_color2) - 20, 255, cv2.THRESH_BINARY)
        images[i] = cv2.equalizeHist(images[i])
    return click_point, puzzle_size, clues_in_column, clues_in_row, pixel_width, images


def read_clue_images(input_images):
    def predict_clue_class(input_img):
        input_img = input_img / 255
        reshaped = input_img.reshape(1, 20, 20, 1)
        # if the model isn't completely sure, it's probably looking at a col/row with just a zero
        if np.amax(model.predict(reshaped)) < 0.997:
            return 0
        return int(model.predict_classes(reshaped))

    clues = []
    zeros = np.full((20, 5), 255)
    for i in input_images:
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
        if num_black_pixels < 15:
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
    return clues


def solve(clues, clues_in_column, clues_in_row, puzzle_size):
    # Turn clue array into array of row/col constraints
    row_constraints = []
    col_constraints = []
    puzzle = np.full((puzzle_size, puzzle_size), -1)
    for i in range(0, 2 * puzzle_size):
        len_clue_arr = clues_in_column if i < puzzle_size else clues_in_row
        clue_diff = 0 if i < puzzle_size else puzzle_size * (clues_in_column - clues_in_row)
        constraints = col_constraints if i < puzzle_size else row_constraints
        constraint = []
        for j in range(0, len_clue_arr):
            clue = clues[clue_diff + i * len_clue_arr + j]
            if clue == -1 and j == len_clue_arr - 1:
                constraint.append(0)
                break
            elif clue == -1:
                continue
            else:
                constraint.append(clue)
        constraints.append(constraint)

    # Solve and return completed puzzle
    if not solver.solve(row_constraints, col_constraints, puzzle):
        raise RuntimeError("The puzzle wasn't able to be solved.")
    if len(puzzle[0]) < 5:
        raise RuntimeError("The solved puzzle size was smaller than expected.")
    return puzzle


def on_press(key):
    if key == exit_key:
        print("Exiting...")
        quit(0)

    if key == start_key:
        # Take a screenshot
        time_begin = datetime.datetime.now()
        img = pyautogui.screenshot()
        img = np.array(img)
        img = img[:, :, ::-1]
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        time_delta = datetime.datetime.now() - time_begin
        ms_diff = int(time_delta.total_seconds() * 1000)
        data = ["Finished getting puzzle image", str(ms_diff) + "ms"]
        print("{:<32} {:>10}".format(*data))

        # Get important data from the screenshotted image
        time_a = datetime.datetime.now()
        try:
            click_point, puzzle_size, clues_in_column, clues_in_row, pixel_width, images = register_image(img_gray)
        except:
            print("!!! There was an error with reading the screenshotted image. Make sure"
                  " that Picross Touch is in full-screen and is in the highest possible"
                  " resolution with a completely empty puzzle grid in view. If an error"
                  " still occurs, try using only the Simple editor and pick a new theme.\n")
            return
        time_delta = datetime.datetime.now() - time_a
        ms_diff = int(time_delta.total_seconds() * 1000)
        data = ["Finished registering image", str(ms_diff) + "ms"]
        print("{:<32} {:>10}".format(*data))

        # Turn clue image array into int array using a machine learning model
        time_a = datetime.datetime.now()
        clues = read_clue_images(images)
        time_delta = datetime.datetime.now() - time_a
        ms_diff = int(time_delta.total_seconds() * 1000)
        data = ["Finished predicting clue images", str(ms_diff) + "ms"]
        print("{:<32} {:>10}".format(*data))

        # Using a solver, turn the clue array into an array of hits and misses
        time_a = datetime.datetime.now()
        try:
            puzzle = solve(clues, clues_in_column, clues_in_row, puzzle_size)
        except:
            print("!!! The image was registered, but the program ran into a problem with"
                  " the solver. Make sure that Picross Touch is in full-screen and is in"
                  " the highest possible resolution with a completely empty puzzle grid"
                  " in view. If an error still occurs, try using only the Simple editor"
                  " and pick a new theme. If still an error occurs, there's likely an"
                  " issue with the digit recognition code.\n")
            return
        time_delta = datetime.datetime.now() - time_a
        ms_diff = int(time_delta.total_seconds() * 1000)
        data = ["Finished solving puzzle", str(ms_diff) + "ms"]
        print("{:<32} {:>10}".format(*data))

        # Using puzzle and pyautogui, automatically fill in the puzzle
        x = click_point[0]
        y = click_point[1]
        for r in puzzle:
            for c in r:
                if c:
                    pyautogui.moveTo(x, y, _pause=False)
                    pyautogui.mouseDown(_pause=False)
                    position1 = pyautogui.position()
                    time.sleep(click_speed)
                    position2 = pyautogui.position()
                    pyautogui.mouseUp(_pause=False)
                    if position1 != position2:
                        print("Detected mouse movement from the user. Stopping...\n")
                        return
                x += pixel_width
            x = click_point[0]
            y += pixel_width
        time_delta = datetime.datetime.now() - time_begin
        ms_diff = int(time_delta.total_seconds() * 1000)
        data = ["Done!", "Total: " + str(ms_diff) + "ms"]
        print("{:<25} {:>17}".format(*data), "\n")


json_file = open("model_trained.json", "r")
loaded_model_json = json_file.read()
json_file.close()
model = model_from_json(loaded_model_json)
model.load_weights("model.h5")
print("Done loading modules and model. Solver is ready to be used. Press " +
      str(start_key)[4:] + " on an empty, full-screened Picross Touch grid"
      " to start the solver.\n")
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
