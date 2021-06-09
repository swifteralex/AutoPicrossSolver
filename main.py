import cv2
import numpy as np
import pickle

# Read screenshotted image
img = cv2.imread("image.png")
imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
height, width = imgGray.shape
print("Finished reading image")

# Get coord for the lower_right_border point of the puzzle
x = round(width / 2)
y = height - 2
background_color_bottom = imgGray[y][x]
while imgGray[y + 1][x] == background_color_bottom:
    y -= 1
while imgGray[y][x + 2] != background_color_bottom:
    x += 1
lower_right_border = [x, y]

# Get coord for the upper_left point and background color of the top left box
background_color_top = imgGray[0][round(width / 2)]
while imgGray[y - 1][x] != background_color_top:
    y -= 1
while imgGray[y][x - 1] != background_color_top:
    x -= 1
x += 40
y += 40
box_color = imgGray[y][x]
while imgGray[y - 1][x] == box_color:
    y -= 1
while imgGray[y][x - 1] == box_color:
    x -= 1
upper_left = [x, y]

# Get anchor points of the puzzle (top left of grid), clicking point, and grid cell colors
while imgGray[y + 1][x] == box_color:
    y += 1
while imgGray[y][x + 1] == box_color:
    x += 1
anchor_point_box = [x, y]
x += 17
y += 17
cell_color1 = imgGray[y][x]
while imgGray[y][x - 1] == cell_color1:
    x -= 1
while imgGray[y - 1][x] == cell_color1:
    y -= 1
anchor_point_grid = [x, y]
while imgGray[y][x + 1] == cell_color1:
    x += 1
while imgGray[y + 1][x] == cell_color1:
    y += 1
click_point = [round((x + anchor_point_grid[0]) / 2), round((y + anchor_point_grid[1]) / 2)]
cell_color2 = imgGray[y + 15][x + 15]

# Get coord for the lower_right point
x = lower_right_border[0]
y = lower_right_border[1]
while imgGray[y][x] != cell_color1 and imgGray[y][x] != cell_color2:
    x -= 1
    y -= 1
lower_right = [x, y]

# Get puzzle size and the maximum number of clues in a column/row
puzzle_size = 0
white_spaces = 0
x = anchor_point_grid[0]
y = anchor_point_grid[1]
while imgGray[y][x] != 0:
    while imgGray[y][x] == cell_color1 or imgGray[y][x] == cell_color2:
        white_spaces += 1
        x += 1
    while imgGray[y][x] != cell_color1 and imgGray[y][x] != cell_color2 and imgGray[y][x] != 0:
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
while imgGray[y][x] != 0:
    start_x = x
    while imgGray[y][x] == cell_color1 or imgGray[y][x] == cell_color2:
        x += 1
    for i in range(0, clues_in_column):
        start_y = round(upper_left[1] + i * (column_height / clues_in_column))
        end_x = x
        end_y = round(upper_left[1] + (i + 1) * (column_height / clues_in_column))
        clue_img = imgGray[start_y:end_y, start_x:end_x]
        images.append(clue_img)
    while imgGray[y][x] != cell_color1 and imgGray[y][x] != cell_color2 and imgGray[y][x] != 0:
        x += 1
x = anchor_point_grid[0]
y = anchor_point_grid[1]
while imgGray[y][x] != 0:
    start_y = y
    while imgGray[y][x] == cell_color1 or imgGray[y][x] == cell_color2:
        y += 1
    for i in range(0, clues_in_row):
        start_x = round(upper_left[0] + i * (row_width / clues_in_row))
        end_y = y
        end_x = round(upper_left[0] + (i + 1) * (row_width / clues_in_row))
        clue_img = imgGray[start_y:end_y, start_x:end_x]
        images.append(clue_img)
    while imgGray[y][x] != cell_color1 and imgGray[y][x] != cell_color2 and imgGray[y][x] != 0:
        y += 1
print("Finished registering image")

# Preprocess clue images
for i in range(0, len(images)):
    images[i] = cv2.resize(images[i], (20, 20), interpolation=cv2.INTER_AREA)
    thresh, images[i] = cv2.threshold(images[i], min(cell_color1, cell_color2) - 20, 255, cv2.THRESH_BINARY)
    images[i] = cv2.equalizeHist(images[i])
print("Finished pre-processing clue images")

# Turn row_images and column_images into arrays of ints using machine learning model
pickle_in = open("model_trained.p", "rb")
model = pickle.load(pickle_in)
print("Finished loading model")


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
                left_column_hit = c if left_column_hit == -1 else left_column_hit
                num_black_pixels += 1
            if i[r][19 - c] == 0:
                right_column_hit = 19 - c if right_column_hit == -1 else right_column_hit

    # if square is blank
    if num_black_pixels < 10:
        clues.append(-1)
        continue

    # run extra check for two digit numbers (sometimes black pixels will bleed onto single-digit images)
    left_verification = False
    right_verification = False
    if right_column_hit - left_column_hit > 15:
        for r in range(0, 20):
            if i[r][left_column_hit + 1] == 0:
                left_verification = True
            if i[r][right_column_hit - 1] == 0:
                right_verification = True

    # if square is two digits
    if right_column_hit - left_column_hit > 15 and left_verification and right_verification:
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

# Write clue array to a .json file
f = open("input.json", "w")
f.write("{\n  \"columns\": [\n")
for i in range(0, puzzle_size):
    f.write("    [")
    for j in range(0, clues_in_column):
        clue = clues[i * clues_in_column + j]
        if clue == -1 and j == clues_in_column - 1:
            f.write("0")
            break
        elif clue == -1:
            continue
        else:
            f.write(str(clue))
            if j != clues_in_column - 1:
                f.write(", ")
    f.write("]")
    if i != puzzle_size - 1:
        f.write(",")
    f.write("\n")
f.write("  ],\n  \"rows\": [\n")
for i in range(0, puzzle_size):
    f.write("    [")
    for j in range(0, clues_in_row):
        clue = clues[puzzle_size * clues_in_column + i * clues_in_row + j]
        if clue == -1 and j == clues_in_row - 1:
            f.write("0")
            break
        elif clue == -1:
            continue
        else:
            f.write(str(clue))
            if j != clues_in_row - 1:
                f.write(", ")
    f.write("]")
    if i != puzzle_size - 1:
        f.write(",")
    f.write("\n")
f.write("  ]\n}")
f.close()

# Write puzzle values to a text file
f = open("puzzle_values.txt", "w")
pixel_width = (lower_right[0] - anchor_point_grid[0]) / puzzle_size
f.write(str(click_point[0]) + "," + str(click_point[1]) + "," + str(pixel_width) + "," + str(puzzle_size))
f.close()
print("Finished writing puzzle data to files")
