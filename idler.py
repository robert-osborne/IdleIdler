#!/usr/bin/env python3
#
# Copyright (c) 2021 Robert Osborne
#
# python3 idler.py --help
#
import argparse
import textwrap
import time
import sys
import os
import configparser
import datetime
import distutils
import json
import math
import glob
import shutil

import pyautogui
import pygetwindow as gw
from PIL import Image, ImageChops, ImageStat
from pathlib import Path

from PIL import ImageGrab
from functools import partial
ImageGrab.grab = partial(ImageGrab.grab, all_screens=True)

# GLOBALS
# Yeah, yeah, globals are bad, sue me
config = configparser.ConfigParser()
top_x = 0
top_y = 0
screen_scale = 2
infinite_loop = False

# Usually 376, 426, etc. and set restart on 386, 436, ...
CHARGE_TIME = 60.0 * 2.5
CHARGE_INTERVAL = 15.0
HAVI_ULT = '8'

APP_NAME = "Idle Champions"

RUNTIME_MINUTES = 20
GEM_LOOPS = 20000
DEFAULT_ADVENTURE = "madwizard"
DEFAULT_LEVEL_DELAY = 20
NUM_FAMILIARS = 6

# TODO: launch checklist
# [ ] Change run to no-modron, just charge briv at end of timer
# [ ] Create backup git on github with full history
# [ ] Squash history 
# [ ] Make public

# TODO: things on my todo list
# [ ] Use flag for restart with Steam image vs. x,y (more stable?)
# [ ] Flag to pause on level 1 and allow Shandie's dash to reset
# [ ] Flag to do briv swapping at each zone complete (heavy duty and occupies entire time)
# [ ] Make champ flags work so don't need team in config file or can modify team in config file (for chores)
# [ ] Add more champs to the familiar leveling code
# [ ] Level Shandie and then wait for dash to trigger

COUNTDOWN = 5
DEFAULT_DELAY = 0.7
DEFAULT_DRAG = 0.1

# Handle retinae vs standard displays by swapping prefixes
first_prefix = "./images/sml-"
second_prefix = "./images/"

# speed characters
have_briv = True
have_binwin = True
have_celeste = True
have_donaar = False
have_deekin = True
have_havilar = True
have_minsc = True
have_sentry = True
have_viper = False
have_shandie = True
have_melf = True

have_gold = True

bounty_size = "small"

verbose = False
debugging = False

MENU_BUTTON_WIDTH = 30
MENU_BUTTON_HEIGHT = 30

def verbose_print(msg):
    global verbose
    if verbose:
        print(msg)


def debug_print(msg):
    global debugging
    if debugging:
        print(msg)


def with_top_offset(off_x, off_y, as_point=False):
    x, y = top_x + off_x, top_y + off_y
    if as_point:
        return pyautogui.Point(x, y)

    return x, y


def menu_location():
    # Point(x=113, y=147)
    # return with_top_offset(0, 0)
    return with_top_offset(32, 73)


def top_location_from_menu(x, y):
    # menu top offset + middle of image
    x, y = x - 32 - 9, y - 73 - 9
    return x, y


def print_reverse_without_offset(x, y, as_point=False):
    x = x - top_x
    y = y - top_y
    print("Offset from top_x, top_y: %d,%d", (x, y))
    # Point(x=113, y=147)
    # return with_top_offset(0, 0)
    if as_point:
        return pyautogui.Point(x, y)
    return x, y


def move_to_menu():
    x, y = menu_location()
    pyautogui.moveTo(x,y)


def move_to_offset(x, y, duration=0.0):
    x, y = with_top_offset(x, y)
    pyautogui.moveTo(x,y, duration=duration)


def click_offset(x, y, duration=0.0, delay=None, tag=None):
    move_to_offset(x, y, duration=duration)
    pyautogui.click()
    if tag:
        verbose_print("%s: clicking on %d, %d" % (tag, x, y))
    if delay:
        time.sleep(delay)


def click_spec_at(x, y, duration=0.0, delay=DEFAULT_DELAY, tag=None):
    # don't use this if modron_specialization is on
    time.sleep(delay)
    click_offset(x, y, duration=duration, delay=delay, tag=tag)


def region_for_screenshot(x, y, width, height):
    x, y = with_top_offset(x, y)
    return (screen_scale * x, screen_scale * y, screen_scale * width, screen_scale * height)


def location_for_screenshot(x,y):
    return screen_scale * x, screen_scale * y


def safe_image_compare(im1, im2, max_mean=30):
    diff = ImageChops.difference(im1, im2)
    stat = ImageStat.Stat(diff)
    # im1.save("safe_im1.png")
    # im2.save("safe_im2.png")
    # verbose_print("mean=%s" % str(stat.mean))
    # verbose_print("rms=%s" % str(stat.rms))

    if (stat.mean[0] + stat.mean[1] + stat.mean[2]) < max_mean:
        return True
    return False


# returns found, ready
# found is True if menu found at expected place
# ready is True if menu is not greyed out (e.g. no Okay button)
menu_blue_png = Image.open("images/menu_blue.png")
menu_blue = menu_blue_png.convert('RGB')
menu_grey_png = Image.open("images/menu_grey.png")
menu_grey = menu_grey_png.convert('RGB')
def check_for_menu():
    x, y = menu_location()
    # pyautogui.moveTo(x, y, duration=0.1)
    x, y = location_for_screenshot(x, y)
    im1 = pyautogui.screenshot(region=(x, y, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)).convert('RGB')
    # im1.save("testmenu.png")
    # menu_blue.save("testblue.png")
    if safe_image_compare(im1, menu_blue):
        return True, True
    if safe_image_compare(im1, menu_grey):
        return True, False
    return False, False


def hunt_for_menu(level_images):
    global top_x, top_y
    pos = pyautogui.position()
    verbose_print("pos=%s" % str(pos))
    # x, y = location_for_screenshot(pos.x, pos.y)
    verbose_print("x,y=%d,%d" % (pos.x, pos.y))
    verbose_print("Configured top_x,top_y = %d,%d" % (top_x, top_y))
    off_x, off_y = 20, 20
    image_size = 30
    region = (screen_scale * (pos.x - off_x), screen_scale * (pos.y - off_y),
              screen_scale * (30+off_x), screen_scale * (30+off_y))
    verbose_print("region=%s" % str(region))
    im1 = pyautogui.screenshot(region=region)
    if verbose:
        im1.save("testmenu.png")
    im1 = im1.convert('RGB')
    found_x = 0
    found_y = 0
    for i in range(0,off_x*2):
        for j in range(0,off_y*2):
            im2 = im1.crop((i, j, i+30, j+30))
            if safe_image_compare(im2, menu_blue):
                if verbose:
                    im2.save("testfoundmenu.png")
                verbose_print("found  i,j=%d,%d" % (i, j))
                # adjust for actual center of the image
                x, y = (pos.x-off_x)*2 + i + image_size/2, (pos.y-off_y)*2 + j + image_size/2
                verbose_print("center x,y=%f,%f" % (x, y))
                x, y = x/screen_scale - 31 - 8, y/screen_scale - 75 - 5
                x = int(x)
                y = int(y)
                verbose_print("Guess: x,y=%f,%f == top_x,top_y=%d,%d " % (x, y, top_x, top_y))
                found_x = x
                found_y = y
                break
        if found_x:
            break
    if not found_x:
        return 0, 0, False
    # Jitter
    for x_jitter in range(-1, 2, 1):
        for y_jitter in range(-1, 2, 1):
            top_x = found_x + x_jitter
            top_y = found_y + y_jitter
            verbose_print("trying jitter %d,%d => %d,%d" % (x_jitter, y_jitter, top_x, top_y))
            level, plus = get_current_zone(level_images=level_images, save=True, tries=1)
            if level > 0:
                print("Zone found %d (at start zone: %s), (on_boss: %s)" % (level, plus, on_boss()))
                return top_x, top_y, True
    return 0, 0, False


def activate_app(app_name, tries=2, reset_top=False):
    for c in range(0,tries):
        try:
            window = gw.getWindowsWithTitle(app_name)[0]
            window.activate()
            time.sleep(0.2)
            active = gw.getActiveWindow()
            if active.title == app_name:
                if reset_top:
                    global top_x, top_y, top_offset
                    top_x, top_y = active.left+1, active.top+top_offset
                    verbose_print("Updating top_x, top_y = %d,%d" % (top_x, top_y))
                return active
            if active.title == "":
                # active menu is a pull down or some crap ... move to a neutral corner
                pyautogui.moveTo(500,500)
            verbose_print("window title: %s try again" % gw.getActiveWindow().title)
        except gw.PyGetWindowException as a:
            # print("%s not found, starting at %s" % (APP_NAME, datetime.datetime.now()))
            verbose_print("WARNING: %s: %s" % (app_name, a, ))
        except Exception as a:
            # print("%s not found, starting at %s" % (APP_NAME, datetime.datetime.now()))
            verbose_print("WARNING: %s: %s" % (app_name, a, ))
    return False


# TODO: group/sort these according to target zone so we find zone quicker when at the end
def load_level_images():
    images = {}
    for f in glob.glob('levels/*.png'):
        debug_print(f)
        images[f] = Image.open(f).convert('RGB').crop((0,0,60,56))
    return images


OFFSET_xx1 = 1829
OFFSET_Y = 14
IMAGE_WIDTH = 60
IMAGE_HEIGHT = 56


# TODO: LEGACY set top_x and top_x by finding menu
def get_menu(tries=10, update=False):
    for i in range(0,tries):
        try:
            # menu_home = locate('menu.png', region=(0,0,400,400))
            menu_home = locate('menu_blue.png', 'menu_grey.png')
            x = menu_home.x * 2 + 1829
            y = menu_home.y * 2 + 14
            return x, y
        except Exception:
            time.sleep(1)


# TODO: make this work
def verify_menu(tries=10, update=False):
    menu_blue_nr = Image.open("menu_blue_nr.png")
    verbose_print("Verifying menu ...")
    for i in range(0,tries):
        # First check using existing top_x, top_y (if exists)
        if top_x != 0 or top_y != 0:
            found, ready = check_for_menu()
            verbose_print("Verifying menu found=%s,ready=%s" % (found, ready))
            if found or ready:
                return True
        else:
            # Image hunt!
            try:
                menu_home = locate('menu_blue.png', 'menu_grey.png')
                # x, y = location_for_screenshot(x, y)
                # x, y = menu_location()
                #
                # found ... all good!
                if menu_home:
                    print("menu_home=%s x,y=%d,%d" % (menu_home, menu_home.x, menu_home.y))
                verbose_print("Verifying menu: locateAll with Image")
                positions = pyautogui.locateAllOnScreen(menu_blue_nr)
                if positions:
                    for pos in positions:
                        print("locateAll: x,y=%d,%d" % (pos.left, pos.top))
                verbose_print("Verifying menu: locateAll with filename")
                positions = pyautogui.locateAllOnScreen("./menu_blue_nr.png")
                if positions:
                    for pos in positions:
                        print("locateAll: x,y=%d,%d" % (pos.left, pos.top))
                verbose_print("Verifying menu: locate with filename")
                return True
            except Exception as e:
                print("image hunt %s" % e)


def get_level_region():
    # grab first zone icon
    region = region_for_screenshot(956, 90, 30, 28)
    return (region[0]+1, region[1]-1, region[2], region[3])


boss = Image.open("levels/bosss.png").convert('RGB')
def on_boss(save_images=False):
    # grab boss icon, on boss if it is black
    region = region_for_screenshot(1154, 93, 22, 22)
    # boss
    # x = x + 2219 - 1829
    # y = y + 10 - 14
    im1 = pyautogui.screenshot(region=region).convert('RGB')
    if save_images:
        im1.save("onboss.png")
        boss.save("theboss.png")
    diff = ImageChops.difference(im1, boss)
    if save_images:
        diff.save("bossdiff.png")
    stat = ImageStat.Stat(diff)
    if (stat.mean[0] + stat.mean[1] + stat.mean[2]) < 20.0:
        return True
    return False


LEVEL_TRYS=20
def get_current_zone(level_images, save=False, tries=LEVEL_TRYS):
    im = None
    for i in range(0,tries):
        verbose_print("get_current_zone attempt %d" % i)
        region = get_level_region()
        raw_im = pyautogui.screenshot(region=region)
        im = raw_im.convert('RGB')
        for name, img in level_images.items():
            diff = ImageChops.difference(im, img)
            stat = ImageStat.Stat(diff)
            if (stat.mean[0] + stat.mean[1] + stat.mean[2]) < 20.0:
                match = name[7:10]
                if match == "bla" or match == "bos":
                    break
                try:
                    level = int(name[7:10])
                    plus = (name[10:11] != 's')
                    return level, plus
                except Exception:
                    break
        if save:
            im.save('my_screenshot%d.png' % i)
        time.sleep(.1)
    return -1, False


def get_current_level(x, y, level_images, save=False):
    im = None
    for i in range(0,LEVEL_TRYS):
        verbose_print("Current level attempt %d" % i)
        im = pyautogui.screenshot(region=(x, y, 60, 56))
        for name, img in level_images.items():
            diff = ImageChops.difference(im.convert('RGB'), img)
            stat = ImageStat.Stat(diff)
            if stat.mean[0] < 0.3 and stat.mean[1] < 0.6 and stat.mean[2] < 0.35:
                match = name[7:10]
                if match == "bla" or match == "bos":
                    break
                try:
                    level = int(name[7:10])
                    plus = (name[10:11] == 's')
                    return level, plus
                except Exception:
                    break
        if save:
            im.save('my_screenshot%d.png' % i)
        time.sleep(.1)
    return -1, False

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def load_player_json():
    user_file = os.path.join(Path.home(),
                             "Library/Application Support/Steam/steamapps/common/IdleChampions",
                             "IdleDragonsMac.app/Contents/Resources/Data/StreamingAssets",
                             "downloaded_files/webRequestLog.txt")
    player_info = []
    with open(user_file, "r") as f:
        for line in f:
            if "current_area" in line:
                info = json.loads(line)
                player_info.append(info)
    return player_info


# repair a broken desktop shortcut
def repair_shortcut():
    # short cut destination
    idle_path = os.path.join(Path.home(), config.get("idler", "steam_app_path"))
    if not os.path.isdir(idle_path):
        print("ERROR: app path is incorrect: %s", idle_path)
        print("ERROR: check that Idle Champions is installed")
        return False

    short_cut = os.path.join(Path.home(), config.get("idler", "shortcut_path"))
    if not os.path.isdir(short_cut):
        print("ERROR: short cut path is missing: %s", short_cut)
        print("ERROR: create the Idle Champions shortcut in Steam")
        return False

    # cp .icns file
    icns_source = os.path.join(idle_path, config.get("idler", "steam_icns"))
    icns_dest = os.path.join(short_cut, config.get("idler", "shortcut_icns"))
    verbose_print("copying %s to %s" % (icns_source, icns_dest))
    shutil.copy(icns_source, icns_dest)

    # cp info.plst
    info_source = "./documentation/Info.plist"
    info_dest = os.path.join(short_cut, "Contents/Info.plist")
    verbose_print("copying %s to %s" % (info_source, info_dest))
    shutil.copy(info_source, info_dest)


def dump_stats(args, player_stats):
    # print(json.dumps(player_stats[0], indent=4, sort_keys=True))
    # return
    bs_tiny = 0
    bs_small = 0
    bs_medium = 0
    bs_large = 0
    bc_tiny = 0
    bc_small = 0
    bc_medium = 0
    bc_large = 0
    # check which line it is in:
    buffs = None
    for stat_block in player_stats:
        if "details" in stat_block:
            buffs = stat_block["details"]["buffs"]
            break

    for buff in buffs:
        if not "buff_id" in buff:
            continue
        buff_id = buff["buff_id"]
        if buff_id == "31":
            bs_tiny = int(buff["inventory_amount"])
        elif buff_id == "32":
            bs_small = int(buff["inventory_amount"])
        elif buff_id == "33":
            bs_medium = int(buff["inventory_amount"])
        elif buff_id == "34":
            bs_large = int(buff["inventory_amount"])
        elif buff_id == "17":
            bc_tiny = int(buff["inventory_amount"])
        elif buff_id == "18":
            bc_small = int(buff["inventory_amount"])
        elif buff_id == "19":
            bc_medium = int(buff["inventory_amount"])
        elif buff_id == "20":
            bc_large = int(buff["inventory_amount"])

    ilvls = bs_tiny * 1 + bs_small*2 + bs_medium * 6 + bs_large * 24
    print("Blacksmith Contracts: %d ilvls" % ilvls)
    print("   tiny=%d x 1 + small=%d x 2 + medium=%d x 6 + large=%d x 24 = %d ilvls" % (
        bs_tiny, bs_small, bs_medium, bs_large, ilvls,
    ))
    tokens = bc_tiny*12 + bc_small*72 + bc_medium * 576 + bc_large * 1152
    runs = tokens / 2500
    print("Bounty Contracts: %d tokens (%d free play runs)" % (tokens, runs))
    print("   tiny=%d x 12 + small=%d x 72 + medium=%d x 576 + large=%d x 1152 = %d tokens (%d runs)" % (
        bc_tiny, bc_small, bc_medium, bc_large, tokens, runs
    ))


# Dangerous, you will accept screenshare from whomever asks ...
# TODO: Need to add an image check for person intended.
def accept_screen_share(is_on):
    if not is_on:
        return
    pyautogui.moveTo(1400, 50, duration=0.0)
    pyautogui.click()
    time.sleep(1.0)
    pyautogui.moveTo(924, 300, duration=0.0)
    pyautogui.click()


def locate(png_name, png_name2=None, click_image_index=0, search_region=None, can_swap=True, screen_shot=None):
    verbose_print("locating %s" % str(png_name))
    global first_prefix, second_prefix
    if not screen_shot:
        screen_shot = pyautogui.screenshot(region=search_region)
        screen_shot.save("test"+png_name)
    if search_region:
        x_off = search_region[0]
        y_off = search_region[1]
    try:
        if click_image_index > 0:
            positions = pyautogui.locateAll(first_prefix+png_name,
                                            screen_shot,
                                            greyscale=0.9,
                                            )
            positions = list(positions)
            box = positions[click_image_index]
            by2 = pyautogui.Point((x_off+box.left+(box.width/2)) / 2, (y_off+box.top+(box.height/2)) / 2)
        else:
            box = pyautogui.locate(first_prefix+png_name,
                                   screen_shot,
                                   grayscale=True,
                                   )
            by2 = pyautogui.Point((x_off+box.left+(box.width/2)) / 2, (y_off+box.top+(box.height/2)) / 2)
        verbose_print("locate(%s) = %s" % (png_name, str(by2)))
        return by2
    except Exception as e:
        verbose_print("locate(%s) = %s" % (png_name, str(e)))
        pass

    # only recurse once per image ...
    if not can_swap:
        if png_name2:
            return locate(png_name2,
                          click_image_index=click_image_index,
                          search_region=search_region,
                          can_swap=True,
                          screen_shot=screen_shot)
        return None

    # swap so we find the right resolution faster next time (won't swap if second also raises)
    verbose_print("swapping from %s to %s" % (first_prefix, second_prefix))
    t = first_prefix
    first_prefix = second_prefix
    second_prefix = t
    return locate(png_name,
                  png_name2=png_name2,
                  click_image_index=click_image_index,
                  search_region=search_region,
                  can_swap=False, screen_shot=screen_shot)


def drag_image(png_name, delta_x, delta_y, duration=DEFAULT_DRAG, delay=DEFAULT_DELAY):
    start = locate(png_name)
    pyautogui.moveTo(start.x, start.y)
    pyautogui.mouseDown(x=start.x, y=start.y, button=pyautogui.LEFT)
    pyautogui.dragRel(delta_x, delta_y, duration=duration, button=pyautogui.LEFT, mouseDownUp=False)
    pyautogui.mouseUp(button=pyautogui.LEFT)
    time.sleep(delay)

    verbose_print("Location: %s" % str(start))
    # print("%s" % str(button)
    # pyautogui.click(button, clicks=2)
    return "Dragged {0}".format(png_name)


def goto_image(png_name, png_name2=None, delay=0.5):
    return click_image(png_name, png_name2=png_name2, delay=delay, click=False)


def click_image(png_name, png_name2=None, delay=0.5, click=True, click_image_index=0):
    global verbose
    button = None
    try:
        button = locate(png_name, click_image_index=click_image_index)
    except Exception:
        if png_name2:
            try:
                button = locate(png_name2, click_image_index=click_image_index)
            except Exception:
                pass
    if not button:
        return ""

    if verbose:
        print("Location: %s" % str(button))
    pyautogui.moveTo(button.x, button.y)
    time.sleep(delay)
    if not click:
        return "Moved"
    pyautogui.click()
    time.sleep(delay)
    # print("%s" % str(button))
    # pyautogui.click(button, clicks=2)
    return "Clicked {0}".format(png_name)


def check_crashed_app():
    try:
        window = gw.getWindowsWithTitle("Problem Report for Idle Champions")[0]
    except Exception:
        window = None
    if not window:
        return False
    print("Detected Crash!")
    # window.activate()
    window.close()
    # click [OK]
    click_ok()
    startup_idle_champions()


def shutdown_app(keyboard=True):
    if keyboard:
        verbose_print("Shutdown Idle Champions with CMD-Q")
        app = activate_app(APP_NAME)
        debug_print("App for CMD-q %s" % app.title)
        if app:
            debug_print("Sending CMD-q")
            pyautogui.hotkey('command', 'q', interval=0.1)
            # pyautogui.keyDown('command')
            # pyautogui.press('q')
            # pyautogui.keyUp('command')
            return

    verbose_print("Shutdown Idle Champions with close")
    try:
        windows = gw.getWindowsWithTitle(APP_NAME)
        for window in windows:
            if window.title == APP_NAME:
                window.close()
                time.sleep(20.0)
                return
            print("Warning: shutdown: '%s' not an exact match for '%s'" % (window.title, APP_name))
        raise gw.PyGetWindowException("No exact match for 'Idle Champions'")
    except Exception as e:
        raise gw.PyGetWindowException("ERROR: shutdown: '%s'" % e)
        return


# Startup using Steam App
# Warning: will shutdown app if running!
def startup_idle_champions(tries=5):
    # TODO: loop on this block until we find menu.png if not using preset top_x, top_y
    # Bring up steam
    print("Restarting Idle Champions")

    for attempt in range(0,tries):

        if config.getboolean("idler", "shortcut_restarting"):
            verbose_print("Starting app with shortcut")
            try:
                short_cut = os.path.join(Path.home(), config.get("idler", "shortcut_path"))
                if not os.path.exists(short_cut):
                    print("ERROR: create a %s desktop short cut using Steam" % short_cut)
                    sys.exit(1)
                result = os.system("open '%s'" % short_cut)
                verbose_print("open shortcut_path (%s) returns %s" % (short_cut, str(result)))
            except Exception as e:
                print("ERROR: could not launch %s" % short_cut)
                print("ERROR: %s" % str(e))
                sys.exit(1)

        elif config.getboolean("idler", "shortcut_start_xy"):
            # TODO: fall back to click_image if this fails
            x = config.getint("steam", "start_x")
            y = config.getint("steam", "start_y")
            pyautogui.moveTo(x, y)
            time.sleep(0.1)
            pyautogui.click()
            time.sleep(1.0)
        else:
            verbose_print("Looking for the steam app")
            # move mouse to top corner
            steam = activate_app("Steam")
            # click [Play] or [Stop]
            verbose_print("Clicking Play/Stop")
            # NOTE: start_with_image is more finicky that start with x,y
            if config.getboolean("steam", "start_with_image"):
                click_image("steam_play.png")

        # now restore the app to front
        print("Waiting for Idle to launch.")
        found_app = False
        ignore_errors = 20
        for s in range(40, 0, -1):
            verbose_print("  %d seconds" % (s/2))
            time.sleep(0.5)

            # bring to front
            try:
                windows = gw.getWindowsWithTitle(APP_NAME)
                for window in windows:
                    if window.title == APP_NAME:
                        found_app = activate_app(APP_NAME, reset_top=True)
                raise gw.PyGetWindowException("No exact match for 'Idle Champions'")
            except gw.PyGetWindowException as a:
                if s <= ignore_errors:
                    print("Not found yet: %s: %s" % (datetime.datetime.now(), a))
                else:
                    verbose_print("Not found yet: %s: %s" % (datetime.datetime.now(), a))
            except Exception as a:
                if s <= ignore_errors:
                    print("Not found yet: %s: %s" % (datetime.datetime.now(), a))
                else:
                    verbose_print("Not found yet: %s: %s" % (datetime.datetime.now(), a))

            if found_app:
                break


        # click ok or find menu for 20 seconds
        if click_ok(startup=True, count=20, ic_app=found_app):
            return True

        # Try killing the app and trying again
        shutdown_app(True)

    return False


def click_ok(count=1, startup=False, ic_app=None):
    # Look for an OK button
    found_ok = False
    move = 50
    # loop attempting a "smart" startup using remembered or hinted top_x, top_y
    known_okays = [(635, 505), (635, 475), (635, 565), (750, 370)]
    ready = False
    found_menu = False
    for s in range(count, 0, -1):
        if ready:
            return True

        # start by clicking on known OK locations to skip movies/okay seeking
        verbose_print("  Madly clicking on possible okay locations")
        for pair in known_okays:
            x, y = with_top_offset(pair[0], pair[1])
            pyautogui.moveTo(x, y, 0.1)
            pyautogui.click(x, y)
            time.sleep(0.1)

        # TODO: set top x, y if not using location hints
        # check for greyed our AND normal menu button,  greyed out find okay, normal we're done!
        verbose_print("  Checking for menu button")
        found, ready = check_for_menu()
        if ready:
            return True
        if found_menu:
            # second check, now need to manually hunt for Okay button
            break
        found_menu = found

        if count != 0:
            try:
                if gw.getActiveWindow().title != APP_NAME:
                    raise Exception("wrong window")
            except Exception as e:
                ic_app = activate_app(APP_NAME)
                time.sleep(0.5)
            time.sleep(0.5)

    return False
    # give up on fast method, now go looking for okay image and reset top_x, top_y using menu image
    for s in range(count, 0, -1):
        try:
            found_level, plus = get_current_level(x, y, level_images, False)
            if found_level > 0:
                print("   Found %d level." % found_level)
                return x,y
        except Exception:
                pass
        if count > 0:
            time.sleep(1.0)
        try:
            x1, y1 = get_menu(1)
            # found!  we can just leave now
            return x1, y1
        except Exception:
            pass
        if not found_ok:
            try:
                found_ok = click_image("okay.png")
                if found_ok:
                    time.sleep(2)
                    print("   Found okay button.")
            except Exception:
                pass
        pyautogui.moveRel(0, move)
        move = -move
        time.sleep(.8)


def foreground_or_start(tries=2):
    # windows = gw.getAllTitles()
    # print("%s" % windows)
    activated = activate_app(APP_NAME, tries=tries, reset_top=True)

    if not activated:
        startup_idle_champions()

    # Don't have top_x, top_y set?  Figure it out!
    if top_x == 0 and top_y == 0:
        verify_menu()

    # im1 = pyautogui.screenshot()
    # im1.save('my_screenshot.png')
    # window = pyautogui.getWindowsWithTitle("Idle Champions")
    # print("window=%s" % str(window))
    # Bring app to foreground
    # try:
    #     click_image('dockicon.png')
    # except Exception:
    #     print("can't find dock icon")


def wrap_it_up():
    # Wait for animation before Continue ...
    foreground_or_start()
    time.sleep(0.5)
    pyautogui.press("r")
    time.sleep(0.9)
    click_offset(559, 491, duration=0.1, delay=0.1, tag="Click Complete")
    for i in range(0,30):
        # Click Skip like Crazy for a bit
        click_offset(1158, 650, duration=0.1, delay=0.1, tag="Click Skip")
        time.sleep(0.1)
    click_offset(635, 595, duration=0.1, delay=0.1, tag="Click Continue")
    time.sleep(5.5)


def wrap_it_up2(position):
    # Wait for animation before Continue ...
    attempt = 0
    complete = ""
    skipped = False
    while attempt < 40:
        print("attempt %s" % attempt)
        if not complete:
            foreground_or_start()
            time.sleep(0.5)
            pyautogui.press("r")
            time.sleep(0.5)
            complete = click_image('complete.png', 'complete2.png')
            if complete:
                print("Completed Adventure")

        if complete and not skipped:
            print("Skipping")
            # position = locate('menu.png')
            for _ in range(0, 16):
                menu_offset_click(position, 430, 120)
            skipped = True

        result = click_image('continue.png')
        if result:
            print("Viewed Adventure Stats")
            break
        time.sleep(0.5)
        attempt += 1
    time.sleep(1.5)


def start_it_up(adventure):
    # Start mad wizard (one should work)
    # Click on city
    click_offset(324, 682, duration=0.1, delay=0.1, tag="Launch Adventure Picker")

    foreground_or_start()
    time.sleep(0.5)
    if adventure == DEFAULT_ADVENTURE:
        click_offset(366, 160, duration=0.1, delay=0.1, tag="Launch Mad Wizard")
    else:
        click_offset(366, 220, duration=0.1, delay=0.1, tag="Launch Terror")

    # time to settle (and for initial hit)
    time.sleep(0.5)
    click_offset(801, 558, duration=0.1, delay=0.1, tag="Click Start Objective")


def menu_offset(pos, x, y):
    x = pos.x + 1380 / 2 + x
    y = pos.y + 895 / 2 + y
    return pyautogui.Point(x,y)


def menu_offset_click(pos, x, y):
    x = pos.x + 1380 / 2 + x
    y = pos.y + 895 / 2 + y
    pyautogui.click(x, y)
    time.sleep(0.2)


def menu_offset_move(pos, x, y):
    x = pos.x + 1380 / 2 + x
    y = pos.y + 895 / 2 + y
    pyautogui.moveTo(x, y, 2.0)
    time.sleep(0.2)


def place_click_familiars(num_familiars):
    pyautogui.keyDown("f")

    click_offset(180, 695, duration=0.1, delay=0.1, tag="Click Damage Leveler")
    click_offset(933, 240, duration=0.1, delay=0.1, tag="1st Battlefield Clicker")
    if num_familiars < 4:
        return
    click_offset(869, 325, duration=0.1, delay=0.1, tag="2nd Battlefield Clicker")
    click_offset(1000, 325, duration=0.1, delay=0.1, tag="3rd Battlefield Clicker")
    if num_familiars < 6:
        return
    click_offset(869, 391, duration=0.1, delay=0.1, tag="5th Battlefield Clicker")
    click_offset(1000, 391, duration=0.1, delay=0.1, tag="6th Battlefield Clicker")

    pyautogui.keyUp("f")


def restart_stacking(args):
    charge_time = args.charge
    shutdown_app(args.keyboard_shutdown)
    time.sleep(charge_time)
    startup_idle_champions()


def charge_briv(level, plus, images, args):
    screenshare = args.screenshare
    charge_time = args.charge
    briv_target = args.target - args.briv_recharge_areas
    restart = args.restart

    GO_BACK_DELAY=9
    pyautogui.press("w")
    time.sleep(0.5)
    pyautogui.press("g")
    time.sleep(0.5)

    print("Recharging Briv starting at %s" % (datetime.datetime.now()))

    # make sure we are not on a boss or zone without a spinner
    while True:
        verbose_print("charge_briv %d %s" % (level, plus))
        if level == briv_target and on_boss():
            verbose_print("    %d & boss; go back one" % level)
            pyautogui.press("left")
            time.sleep(GO_BACK_DELAY)
            break
        elif level == briv_target:
            verbose_print("    Just go for it %d" % level)
            break
            pyautogui.press("left")
            time.sleep(GO_BACK_DELAY)
            try:
                level, plus = get_current_level(x, y, level_images, False)
            except Exception:
                break
        elif level == briv_target + 6 and plus:
            pyautogui.press("left")
            time.sleep(GO_BACK_DELAY)
            pyautogui.press("left")
            time.sleep(GO_BACK_DELAY)
            break
        else:
            verbose_print("   Done")
            break

    # restart charging ... so good
    if restart:
        shutdown_app(args.keyboard_shutdown)
        accept_screen_share(screenshare)
        time.sleep(charge_time)
        startup_idle_champions()
        time.sleep(5.0)

    # manual charging ... still better than a poke in the eye with a sharp stick
    else:
        charging = charge_time
        while charging > 0.0:
            verbose_print("Charging Briv: %f more seconds" % (charging))
            if charging > CHARGE_INTERVAL:
                accept_screen_share(screenshare)
                foreground_or_start()
                if on_boss():
                    print("%d & boss; go back one" % level)
                    pyautogui.press("left")
                time.sleep(CHARGE_INTERVAL)
                charging -= CHARGE_INTERVAL
            else:
                time.sleep(charging)
                break

    # start going forward again ... why is this sooooooo slow
    print("Resuming ...")
    foreground_or_start()
    pyautogui.press("left")
    time.sleep(1.5)
    pyautogui.press("q")
    time.sleep(2.0)
    pyautogui.press("g")
    time.sleep(2.0)
    pyautogui.press("q")

    return True


def remove_familiars(position, ult):
    pyautogui.keyDown("f")
    time.sleep(0.1)
    offset = 230
    if ult == 4:
        offset += 90
    if ult == 5:
        offset += 120
    menu_offset_click(position, offset, 10)
    menu_offset_click(position, offset, 10)
    pyautogui.keyUp("f")
    pass


def place_other_familiars(position, familiars):
    pyautogui.keyDown("f")
    # place more click familiars
    # drag_image('familiar.png', 135, -135)
    if familiars >= 3:
        menu_offset_click(position, 135, -195)

    # drag_image('familiar.png', 275, -135)
    if familiars >= 4:
        menu_offset_click(position, 275, -195)

    # drag_image('familiar.png', 135, -195)
    if familiars >= 5:
        menu_offset_click(position, 135, -135)

    # drag_image('familiar.png', 275, -195)
    if familiars >= 6:
        menu_offset_click(position, 275, -135)
        # drag_image('familiar.png', 195, -255)
    if familiars >= 7:
        menu_offset_click(position, 195, -255)

    pyautogui.keyUp("f")
    return

    # binwin (slot 3)
    # drag_image('familiar.png', -225, 165)
    menu_offset_click(position, -225, 165)
    if familiars <= 8:
        return
    # Shandie (slot 7)
    drag_image('familiar.png', 100, 165)
    if familiars <= 9:
        return
    # jarlaxle or stoki (slot 4)
    drag_image('familiar.png', -120, 165)
    if familiars <= 10:
        return
    # Deekin (slot 1)
    # drag_image('familiar.png', -450, 165)
    pyautogui.keyUp("f")

SPECS = {
    "1_of_2": {"x": 515, "y": 585},
    "2_of_2": {"x": 760, "y": 585},
    "1_of_3": {"x": 384, "y": 585},
    "2_of_3": {"x": 635, "y": 585},
    "3_of_3": {"x": 885, "y": 585},
}
TEAM_DEFINITIONS = {
    # Speedsters
    "briv":    {"key": "f5",  "bs": 19, "as": 30, "spec": "1_of_3", "short":"-B",},
    "shandie": {"key": "f6",  "bs": 24, "as": 30, "spec": "1_of_3", "short":"-S",},
    "havi":    {"key": "f10", "bs": 21, "as":  0, "spec": "1_of_2", "short":"-H",},
    "deekin":  {"key": "f1",  "bs": 16, "as":  0, "spec": "3_of_3", "short":"-D",},
    "melf":    {"key": "f12", "bs": 12, "as": 30, "spec": "2_of_3", "short":"-M",},
    "sentry":  {"key": "f4",  "bs": 20, "as": 30, "spec": "2_of_3", "short":"-Y",},
    "hew":     {"key": "f8",  "bs": 15, "as": 30, "spec": "2_of_2", "short":"-W",},

    # Extras
    "viper":   {"key": "f7",  "bs": 12, "as": 30, "spec": "2_of_2", },
    "binwin":  {"key": "f3",  "bs": 21, "as": 30, "spec": "2_of_2", },
    "drizzt":  {"key": "f9",  "bs": 19, "as": 30, "spec": "1_of_2", },
    "omin":    {"key": "f3",  "bs": 20, "as": 70, "spec": "2_of_3", },
    "jarlaxle":{"key": "f4",  "bs": 12, "as": 30, "spec": "2_of_2", },

    # fix
    "minsc":   {"key": "f7",  "bs": 4,  "as": 30, "spec": "2_of_2", },
    "strix":   {"key": "f11", "bs": 16, "as": 30, "spec": "3_of_3", },
    "hitch":   {"key": "f7",  "bs": 4,  "as": 30, "spec": "2_of_2", },
}


def level_champ_with_keys(args, champ, between_champs=0.1):
    if champ not in TEAM_DEFINITIONS:
        print('ERROR: champ "%s" has no definition for F Key leveling' % champ)
        return None
    definition = TEAM_DEFINITIONS[champ]
    verbose_print("Leveling %s %s" % (champ, definition))
    for c in range(0,definition['bs']):
        pyautogui.press(definition['key'])
    time.sleep(DEFAULT_DELAY)
    if not args.modron_specialization:
        spec = SPECS[definition["spec"]]
        click_spec_at(spec["x"], spec["y"], delay=0.3, tag=champ)
    time.sleep(between_champs)
    return definition["key"]


def level_team_with_keys(args, team, between_champs=0.1):
    have_shandie = ("shandie" in team)
    have_hew = ("hew" in team)
    leveling_keys = []
    if have_shandie:
        key = level_champ_with_keys(args, "shandie", between_champs=between_champs)
        leveling_keys.append(key)
    if "havi" in team:
        key = level_champ_with_keys(args, "havi", between_champs=between_champs)
        leveling_keys.append(key)
        # fire ult! once
        pyautogui.press("1")
        if have_shandie:
            pyautogui.press("2")
    for champ in team.split(','):
        champ = champ.strip()
        if champ in ["shandie", "havi"]:
            continue
        key = level_champ_with_keys(args, champ, between_champs=between_champs)
        leveling_keys.append(key)

    # TODO: wait here for shandie to start dashing ...

    # Load the Formation
    pyautogui.press('q')
    time.sleep(DEFAULT_DELAY)
    pyautogui.press('g')
    time.sleep(DEFAULT_DELAY)

    # more rounds of leveling based on those F keys
    for i in range(0, 20):
        for f_key in leveling_keys:
            pyautogui.press(f_key)

    if have_hew:
        for i in range(0, 20):
            pyautogui.press(args.hew_ult)
            time.sleep(0.1)

    return leveling_keys


def click_third_spec(delay=0.0):
    if click_image("select.png", click_image_index=2):
        pyautogui.moveRel(0, -120, duration=0.1)
        time.sleep(delay)


def click_second_spec(delay=0.0):
    if click_image("select.png", click_image_index=1):
        pyautogui.moveRel(0, -120, duration=0.1)
        time.sleep(delay)


def click_first_spec(delay=0.0):
    click_image("select.png")
    pyautogui.moveRel(0, -120, duration=0.1)
    time.sleep(delay)
    return
    pyautogui.moveRel(550, 0, duration=0.1)
    for i in range(0, 8):
        pyautogui.click()


def click_with_position(image, target, offset_x=0, offset_y=0, click=True):
    verbose_print("click_with_position(%s,%s)" % (image, str(target)))
    if not target:
        time.sleep(0.2)
        target = locate(image)
    pyautogui.moveTo(target.x+offset_x, target.y+offset_y, duration=0.0)
    time.sleep(0.1)
    if click:
        pyautogui.click()
    time.sleep(0.2)
    return target


def handle_extras(args):
    if args.F1:
        pyautogui.press("f1")
    if args.F2:
        pyautogui.press("f2")
    if args.F3:
        pyautogui.press("f3")
    if args.F4:
        pyautogui.press("f4")
    if args.F5:
        pyautogui.press("f5")
    if args.F6:
        pyautogui.press("f6")
    if args.F7:
        pyautogui.press("f7")
    if args.F8:
        pyautogui.press("f8")
    if args.F9:
        pyautogui.press("f9")
    if args.F10:
        pyautogui.press("f10")
    if args.F11:
        pyautogui.press("f11")
    if args.F12:
        pyautogui.press("f12")


def get_bool_config(cfg, key, default):
    try:
        return bool(distutils.util.strtobool(cfg['idler'][key]))
    except Exception:
        return default


def add_champs_to_parser(parser):
    for name, v in TEAM_DEFINITIONS:
        lc = name.lower()
        parser.add_argument("--"+lc, help="Use "+name,
                            default=False,
                            dest="use_"+lc,
                            action="store_true")
        parser.add_argument("--no-"+lc, help="Don't use "+name,
                            dest="use_"+lc,
                            action="store_false")


def load_config():
    global config, top_x, top_y
    # Load defaults
    defaults = "./defaults.cfg"
    if not os.path.exists(defaults):
        print("Missing %s file" % defaults)
        sys.exit(0)
    config.read(defaults)
    # load local overrides
    local = "./local.cfg"
    if os.path.exists(local):
        config.read(local)
    # Get the .idler overrides, these should be what was created by ./idler.py init
    config_path = os.path.join(Path.home(), '.idler')
    if os.path.exists(config_path):
        config.read(config_path)

    if config.getboolean("idler", "use_top_hint"):
        top_x = config.getint("idler", "top_hint_x")
        top_y = config.getint("idler", "top_hint_y")
        verbose_print("Config top_x,top_y = %d,%d" % (top_x, top_y))


# object to support logging all of tracking logs to a permanent file
class Tee(object):
    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()


# object to support logging all of tracking logs to a permanent file
class Tracker(object):
    file = None
    started = False
    verbose = False
    zones = None
    bosses_per_run = None
    start_of_session = None

    total_runs = 0
    start_of_run = None
    longest_run = None
    bosses_this_session = None

    def __init__(self, now, zones=0, verbose=False, logfile=None, log_mode="a"):
        self.start_of_session = None
        self.start_of_run = None
        self.zones = zones
        self.bosses_per_run = self.zones / 5

        self.bosses_this_session = 0
        self.total_runs = 0
        self.started = False

        if logfile:
            self.file = open(logfile, log_mode)

    def elapsed(self, td):
        seconds = td.total_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return hours, minutes, seconds

    def start_loop(self, now, level, plus):
        if not self.started:
            self.start_of_run = now
            self.start_of_session = now
            self.started = True
            return

        self.total_runs += 1
        print("Loop %d started: %s: %d%s" % (self.total_runs, now, level, "+" if plus else ""))

        self.bosses_this_session += self.bosses_per_run

        run_elapsed = now - self.start_of_run
        run_bph = float(self.bosses_per_run) / float(run_elapsed.total_seconds()) * 60.0 * 60.0
        run_hours, run_minutes, run_seconds = self.elapsed(run_elapsed)

        session_elapsed = now - self.start_of_session
        session_bph = float(self.bosses_this_session) / float(session_elapsed.total_seconds()) * 60.0 * 60.0
        session_hours, session_minutes, session_seconds = self.elapsed(session_elapsed)

        print("Session: %d:%d:%d BPH: %.2f Run: %d:%d:%d BPH: %.2f" % (
            session_hours, session_minutes, session_seconds,
            session_bph,
            run_hours, run_minutes, run_seconds,
            run_bph,
        ))

        self.start_of_run = now

    def flush(self):
        self.file.flush()

    def start_tracking(self, now, level, plus):
        print("Gem farming session started: %s: with detected level %d%s" % (now, level, "+" if plus else ""))


epilog="""Commands:
    The following commands are available:

    1. Gem Farming with or without Modron Automation (see README for more details):

        ./idler.py modron 
        ./idler.py no-modron 

    2. Buying bounties quickly, the following commands will by 50 bounties of the given type:

        ./idler.py small 5 
        ./idler.py medium 5 

    3. Opening silver chests quickly, the following command will open 5 batches of 50 silver chests:

        ./idler.py silver 5

    4. Quick reset stacking, assuming Briv is at a level where he can no longer advance:

        ./idler.py --charge 15 stack 5
"""


def main_method():
    global top_x, top_y, top_offset, debugging, verbose, infinite_loop
    load_config()

    # get defaults from config file
    # have_briv = get_bool_config(config, "use_briv", have_briv)
    # have_havilar = get_bool_config(config, "use_havilar", have_havilar)
    # have_binwin = get_bool_config(config, "use_binwin", have_binwin)
    # have_deekin = get_bool_config(config, "use_deekin", have_deekin)
    # have_sentry = get_bool_config(config, "use_sentry", have_sentry)
    # have_shandie = get_bool_config(config, "use_shandie", have_shandie)
    # have_melf = get_bool_config(config, "use_melf", have_melf)
    # have_hew = get_bool_config(config, "use_hew", have_melf)

    steam_start_with_image = get_bool_config(config, "steam_start_with_image", True)
    steam_start_x = get_bool_config(config, "steam_start_x", True)
    default_charge_time = config.getfloat("idler", "briv_charge_time")
    briv_restart_charging = config.getboolean("idler", "briv_restart_charging")
    briv_boss_handling = config.getboolean("idler", "briv_boss_handling")

    level_images = load_level_images()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(epilog)
    )

    parser.add_argument("--tee", help="Also send output to a logfile (appending)",
                        default=None,
                        type=str)
    parser.add_argument("--keyboard-shutdown",
                        dest="keyboard_shutdown",
                        default=config.getboolean("idler", "keyboard_shutdown"),
                        help="Shutdown %s by sending CMD-Q" % APP_NAME, action="store_true")
    parser.add_argument("--no-keyboard-shutdown", "--close",
                        dest="keyboard_shutdown",
                        help="Shutdown %s by closing the app." % APP_NAME,
                        action="store_false")

    # meta
    parser.add_argument("-m", "--mirt", help="Set reasonable defaults for a Mirt run (no Deekin)",
                        action="store_true")
    parser.add_argument("-v","--vajra", help="Set reasonable defaults for a Vajra run (no Minsc)",
                        action="store_true")
    parser.add_argument("-a", "--adventure", default=DEFAULT_ADVENTURE,
                        help="Adventure to run (madwizard, terror) (default %s)" % DEFAULT_ADVENTURE,
                        type=str)

    parser.add_argument("-f", "--familiars", default=NUM_FAMILIARS,
                        help="How many familiars do you have (default %d)" % NUM_FAMILIARS, type=int)
    parser.add_argument("--target", default=config.getint("idler", "modron_target"),
                        help="What zone is your Modron core set to restart (default %d)" % config.getint("idler", "modron_target"),
                        type=int)
    parser.add_argument("--briv-recharge-areas", "--briv-areas", default=config.getint("idler", "briv_recharge_areas"),
                        help="How many areas before your Modron area goal should Briv start recharging (default is %s which works for Triple Skip Briv, use 15 for Quad skip Briv)" % config.getint("idler", "briv_recharge_areas"),
                        type=int)
    parser.add_argument("--charge", default=default_charge_time,
                        help="Amount of time for Briv charging, either method (default %f)" % default_charge_time,
                        type=float)
    parser.add_argument("--no-boss", default=default_charge_time,
                        help="Amount of time for Briv charging, either method (default %f)" % default_charge_time,
                        type=float)

    #how to spec
    parser.add_argument("--specialization", default=config.getboolean("idler", "modron_specialization"),
                        dest="modron_specialization",
                        help="Specialization automaticaly done by modron.",
                        action="store_true")
    parser.add_argument("--no-specialization", "--fkeys",
                        dest="modron_specialization",
                        help="Specialization not automaticaly done by modron.",
                        action="store_false")

    #skip boss
    parser.add_argument("--briv-boss", default=briv_boss_handling,
                        dest="briv_boss",
                        help="Remove Briv if on a boss (Quad Briv) via formation 'e'",
                        action="store_true")
    parser.add_argument("--no-briv-boss",
                        dest="briv_boss",
                        help="No special handling for Briv on bosses",
                        action="store_false")
    #restart
    parser.add_argument("--restart", default=briv_restart_charging,
                        dest="restart",
                        help="Briv charging via quit/restart",
                        action="store_true")
    parser.add_argument("--no-restart", help="Briv charging by waiting.",
                        dest="restart",
                        action="store_false")
    parser.add_argument("--charge-shandie", default=config.getint("idler", "charge_shandie"),
                        dest="charge_shandie",
                        help="Charge Shandie's dash on startup (default %d seconds)" % 0,
                        type=int)

    parser.add_argument("--size", default="small",
                        help="Size of bounties to open (small or medium,default small)",
                        type=str)
    parser.add_argument("-r", "--runloops", default=GEM_LOOPS,
                        help="How many loops gem run (default %d)" % GEM_LOOPS,
                        type=int)
    parser.add_argument("-l", "--level", default=DEFAULT_LEVEL_DELAY,
                        help="How many seconds to wait before leveling champs (default %d)" % DEFAULT_LEVEL_DELAY,
                        type=int)

    parser.add_argument("--F1", help="Activate slot 1st hero (1 level).", action="store_true")
    parser.add_argument("--F2", help="Activate slot 2nd hero (1 level).", action="store_true")
    parser.add_argument("--F3", help="Activate slot 3rd hero (1 level).", action="store_true")
    parser.add_argument("--F4", help="Activate slot 4th hero (1 level).", action="store_true")
    parser.add_argument("--F5", help="Activate slot 5th hero (1 level).", action="store_true")
    parser.add_argument("--F6", help="Activate slot 6th hero (1 level).", action="store_true")
    parser.add_argument("--F7", help="Activate slot 7th hero (1 level).", action="store_true")
    parser.add_argument("--F8", help="Activate slot 8th hero (1 level).", action="store_true")
    parser.add_argument("--F9", help="Activate slot 9th hero (1 level).", action="store_true")
    parser.add_argument("--F10", help="Activate slot 10th hero (1 level).", action="store_true")
    parser.add_argument("--F11", help="Activate slot 11th hero (1 level).", action="store_true")
    parser.add_argument("--F12", help="Activate slot 12th hero (1 level).", action="store_true")



    parser.add_argument("--modron", help="Depend on Modron to reset and level.",
                        default=config.getboolean('idler', 'use_modron'),
                        dest="use_modron",
                        action="store_true")
    parser.add_argument("--no-modron", help="Manual resetting of levels.",
                        dest="use_modron",
                        action="store_false")

    parser.add_argument("--save_mismatch", help="When checking level, save any mismatches.",
                        action="store_true")
    parser.add_argument("--in-progress", help="Start up with a game in progress.",
                        action="store_true")

    parser.add_argument("-O", "--odds", help="Briv odds of jumping",
                        type=float, default=99.0)
    parser.add_argument("--header", help="Height of the Idle Champions application header",
                        type=int,
                        default=config.getint("idler", "header_height"))
    parser.add_argument("--countdown",
                        help="Seconds to wait before starting command (default %d)" % COUNTDOWN,
                        type=int,
                        default=COUNTDOWN, )
    parser.add_argument("-c", "--confirm_buy", help="Confirm buying gold chests (skips Yes/No prompt).",
                        action="store_true")
    parser.add_argument("-x", "--experimental", help="Don't use this.",
                        action="store_true")
    parser.add_argument("--verbose", help="Debugging aid.", action="store_true")
    parser.add_argument("--debug", help="Debugging aid, very noisy.", action="store_true")
    parser.add_argument("--screenshare", "--ss",
        help="Screen share accept active.",
        action="store_true")

    parser.add_argument('-F', '--formation', metavar='formation', type=str,
        help="Formation key to use to set initial formations and familiars",
        default=None)

    parser.add_argument("--havi-ult", default=config.get('idler', 'havi_ult'),
                        help="Key that hits Havi's ult. (default %s)" % config.get('idler', 'havi_ult'),
                        type=str)
    parser.add_argument("--hew-ult", default=config.get('idler', 'hew_ult'),
                        help="Key that hits Hews's ult. (default %s)" % config.get('idler', 'hew_ult'),
                        type=str)

    # Commands and arguments
    parser.add_argument('command', metavar='command', type=str, nargs="?",
                        help="""Action to perform (modron, stats, run, silver, stack, bounty, keep-alive)
                        run: loop on adventures for N minutes to acquire gems and/or patron currency
                        press: press the specified key every few seconds
                        buy: buy N gold chests """, default="stats")
    parser.add_argument('loops', metavar='N', type=int, nargs="?",
                        help="""Argument (N) to the action (number of chests/minutes)""",
                        default=0)
    parser.add_argument('extras', metavar='N', type=int, nargs="*",
                        help="""Argument (N+) to the action (e.g. bs contracts)""",
                        default=0)
    args = parser.parse_args()

    verbose = args.verbose
    debugging = args.debug

    verbose_print("Command = %s" % args.command)
    debug_print("Debugging On")

    top_offset = args.header
    patron = "None"

    speed_team = config.get("idler", "speed_team")

    if args.tee:
        Tee(args.tee, "a")

    if args.vajra:
        speed_team = config.get("idler", "vajra_speed_team")
        patron = "Vajra"
    if args.mirt:
        speed_team = config.get("idler", "mirt_speed_team")
        patron = "Mirt"

    # Apply args to speed team
    have_briv = False
    if "briv" in speed_team:
        have_briv = True

    champs_list = []
    if have_briv:
        champs_list.append("briv")
    if have_celeste:
        champs_list.append("celeste")
    if have_donaar:
        champs_list.append("donaar")
    if have_deekin:
        champs_list.append("deekin")
    if have_shandie:
        champs_list.append("shandie")
    if have_melf:
        champs_list.append("melf")
    if have_minsc:
        champs_list.append("minsc")
    if have_viper:
        champs_list.append("viper")
    if have_binwin:
        champs_list.append("binwin")
    if have_havilar:
        champs_list.append("havilar")
    if have_sentry:
        champs_list.append("sentry")
    if have_gold:
        champs_list.append("[gold]")
    champs = ",".join(champs_list)

    if args.screenshare:
        print("Sreenshare mode!")

    if args.command == "pytest":
        print("merged: %s" % list(pyautogui.locateAllOnScreen('./merged.png')))
        print("merged2: %s" % list(pyautogui.locateAllOnScreen('./merged2.png')))
        print("merged3: %s" % list(pyautogui.locateAllOnScreen('./merged3.png')))
        sys.exit(0)

    if args.command == "stats":
        player_stats = load_player_json()
        dump_stats(args, player_stats)
        print("Champs you can put in your team:")
        champs = ",".join([key for key in TEAM_DEFINITIONS.keys()])
        print("    %s" % champs)
        sys.exit(0)

    if args.command == "init":
        print("Configuring system, this will take a minute or two ...")
        time.sleep(5)
        init_config_path = os.path.join(Path.home(), '.idler')
        init_config = configparser.ConfigParser(allow_no_value=True)
        if os.path.exists(init_config_path):
            print("Updating ~/.idler file")
            init_config.read(init_config_path)
        else:
            print("Creating ~/.idler file")
        if not config.getboolean("idler", "shortcut_restarting"):
            print("Looking for the steam app")
            # move mouse to top corner
            steam = activate_app("Steam")
            time.sleep(1)
            # click [Play] or [Stop]
            print("Looking for Play or Stop")
            try:
                location = locate("steam_play.png", "steam_stop.png")
                if "steam" not in init_config:
                    init_config.add_section("steam")
                init_config["steam"]["; middle pixel of the Idle Champions [play] button on Steam"] = None
                init_config["steam"]["start_with_image"] = "no"
                init_config["steam"]["start_x"] = str(int(location.x))
                init_config["steam"]["start_y"] = str(int(location.y))
                print("Found Steam Play/Stop Location: %s" % str(location))
            except Exception as e:
                print("Error finding Steam Play/Stop location: %s" % str(e))

        print("Hover over the blue menu icon in the top left corner of the Idle Champions game.  Do not click!")
        time.sleep(5.0)
        print("Looking for the %s app" % APP_NAME)
        ic_app = activate_app(APP_NAME)
        time.sleep(1)
        for tries in range(0, 2):
            try:
                # location = locate("menu.png")
                # top_x, top_y = top_location_from_menu(int(location.x), int(location.y))
                print("Screen shot in ", end='')
                for i in range(10,0,-1):
                    print('%d ...' % i, end='', flush=True)
                    time.sleep(1)
                top_x, top_y, found = hunt_for_menu(level_images)
                if not found:
                    continue
                if "idler" not in init_config:
                    init_config.add_section("idler")
                init_config["idler"]["; top left pixel of the app when launched"] = None
                init_config["idler"]["use_top_hint"] = "yes"
                init_config["idler"]["top_hint_x"] = str(top_x)
                init_config["idler"]["top_hint_y"] = str(top_y)
                print("Found app top x,y: %d,%d" % (top_x, top_y))
                break
            except Exception as e:
                print("Error finding Menu Icon location: %s" % str(e))

        print("Checking init with current zone ...")
        level, plus = get_current_zone(level_images=level_images, save=True, tries=1)
        if level > 0:
            print("Zone found %d (at start zone: %s), (on_boss: %s)" % (level, plus, on_boss()))
        else:
            print("Zone not found, check again with ./idler.py zone")

        print("Updating ~/.idler.py")
        with open(init_config_path, 'w') as f:
            f.write("# created by idler.py, a Idle Champions script engine\n")
            f.write("# Warning: edit at on risk\n")
            init_config.write(f)
        sys.exit(0)

    if args.command == "Tracker" or args.command == "Track":
        print("Test Tracker ...")
        try:
            now = datetime.datetime.now()
            tracker = Tracker(now=now-datetime.timedelta(minutes=11, seconds=12),
                              zones=args.target,
                              verbose=verbose,)
            print("start track %s" % now)
            tracker.start_tracking(now, 20, False)
            print("start loop %s" % now)
            tracker.start_loop(now, 221, False)
            now = now + datetime.timedelta(minutes=11, seconds=12)
            print("start loop %s" % now)
            tracker.start_loop(now, 1, False)
            now = now + datetime.timedelta(minutes=10, seconds=33)
            print("start loop T %s" % now)
            tracker.start_loop(now, 1, True)
            now = now + datetime.timedelta(minutes=12, seconds=1)
            print("start loop %s" % now)
            tracker.start_loop(now, 6, False)
        except Exception as e:
            print("Error: %s" % str(e))
        sys.exit(0)

    if args.command == "testhunt":
        print("Test Hunt for Menu ...")
        print("Screen shot in ", end='')
        for i in range(10,0,-1):
            print('%d ...' % i, end='', flush=True)
            time.sleep(1)
        for round in range(0,5):
            print("")
            print("######## Round %d ############" % round)
            x, y, found = hunt_for_menu(level_images)
            if round == 4:
                break
            print("Next screen shot in ", end='')
            for i in range(5,0,-1):
                print('%d ...' % i, end='', flush=True)
                time.sleep(1)
        sys.exit(0)

    if args.command == "mouse":
        print("You have 5 seconds to hover ...")
        time.sleep(5)
        pos = pyautogui.position()
        print("raw mouse: %s" % str(pos))
        off_x, off_y = print_reverse_without_offset(int(pos.x), int(pos.y))
        # print("offset from top_x,top_y = %d, %d" % (off_x, off_y))
        sys.exit(0)

    if args.command == "zone":
        print("Looking for the %s app" % APP_NAME)
        time.sleep(1)
        found_app = activate_app(APP_NAME, reset_top=True)
        time.sleep(1)
        level, plus = get_current_zone(level_images, True)
        print("Zone found %d (at start zone: %s), (on_boss: %s)" % (level, plus, on_boss()))
        if level <= 0:
            print("Could not find zone, zone image saved in my_screenshot*.png")
        sys.exit(0)

    no_modron_commands = ["run", "no-core", "no-modron", ]
    if args.command in no_modron_commands:
        if args.use_modron:
            print("WARNING: Modron mode enabled but you are using the No Modron run command.")
        print("Patron:%s / Familiars:%d / Minutes:%d / Team:%s (CTRL-C to stop)" % (
            patron, args.familiars, args.loops, speed_team))

    if args.command == "buy":
        confirmation_msg = ""
        if not args.confirm_buy:
            confirmation_msg = "type Y to buy or N/"
        msg = ("Buy %d gold chests for %d gems (%sCTRL-C to stop)" % (
            args.loops, args.loops * 500, confirmation_msg))
        if args.confirm_buy:
            print(msg)
        else:
            agreed = query_yes_no(msg, default="no")
            if not agreed:
                sys.exit(1)

    while args.command == "goto":
        pyautogui.moveTo(1400, 50, duration=2.0)
        pyautogui.click()
        pyautogui.moveTo(924, 292, duration=2.0)
        pyautogui.click()
        time.sleep(5.0)
        print("mouse: %s" % str(pyautogui.position()))

    if args.command == "bs":
        tiny = args.loops
        small = args.extras[0]
        medium = args.extras[1]
        large = args.extras[2]
        ilvls = tiny * 1 + small*2 + medium * 6 + large * 24
        print("tiny=%d x 1 small=%d x 2 medium=%d x 6 large=%d x 24 = %d ilvls" % (
            tiny,small,medium,large, ilvls,
            ))
        
        sys.exit(1)

    if args.command == "bc":
        small = args.loops
        medium = args.extras[0]
        large = args.extras[1]
        tokens = small*72 + medium * 576 + large * 1152
        runs = tokens / 2500
        print("small=%d x 72 medium=%d x 576 large=%d x 1152 = %d tokens (%d runs)" % (
            small,medium,large, tokens, runs
            ))
        
        sys.exit(1)

    reduction = 0.032
    if args.command == "briv4":
        reduction = 0.04
        args.command = "briv"
    if args.command == "briv3":
        args.command = "briv"

    while args.command == "briv":
        stacks = float(args.loops)
        jumps = 0
        print("stacks=%f jumps=%d odds=%f percent=%f" % (stacks, jumps, args.odds, reduction))
        while stacks > 50.0:
            stacks -= stacks * reduction
            stacks = math.floor(stacks)
            skipped = jumps * 3
            levels = jumps * 3 + float(jumps) / args.odds * 100.0
            print("stacks=%f jumps=%d skipped=%d levels=%d" % (
                stacks, jumps, skipped, levels))
            jumps += 1
        sys.exit(1)

    while args.command == "cmp":
        im1 = Image.open("my_screenshot0.png").convert('RGB')
        im2 = Image.open("levels/511.png").convert('RGB')
        diff = ImageChops.difference(im1, im2)
        result = ImageStat.Stat(diff)
        print("mean=%s" % str(result.mean))
        print("rms=%s" % str(result.rms))
        diff.save('diff.png')
        if diff.getbbox():
            print("Not same, check diff.png, %s" % str(diff.getbbox()))
        else:
            print("Same")
        sys.exit(1)

    if args.command == "repair_shortcut":
        result = repair_shortcut()
        sys.exit(0 if result else 1)

    # Commands above this line don't require Idle Champions to be running
    # ########################################################################
    # Start idle champions and foreground it

    print("Starting/Foregrounding Idle Champions")
    if args.countdown > 0:
        print("Script will start in ...", end='', flush=True)
        for s in range(args.countdown, 0, -1):
            print(" %d ..." % s, end='', flush=True)
            time.sleep(1.0)
        print("now")

    foreground_or_start(tries=5)
    time.sleep(1.0)

    # TODO: check that top_x and top_y have been set
    verbose_print("Using top_x,top_y = %d,%d" % (top_x, top_y))

    loops = 0
    crashes = 0

    # ########################################################################
    # Commands below this line require Idle Champions to be running

    if args.command == "testfkey":
        print("level_team_with_keys(args,[%s])" % speed_team)
        level_team_with_keys(args,speed_team, between_champs=1.0)
        sys.exit(0)

    if args.command == "teststart":
        print("Test Startup Complete")
        sys.exit(0)

    while args.command == "zap":
        pyautogui.press("e")
        time.sleep(5.0)

    while args.command == "keep-alive":
        time.sleep(args.loops)
        print("Checking for game at %s" % datetime.datetime.now())
        foreground_or_start()
        continue

    while args.command == "goto":
        pyautogui.moveTo(2028, 20, duration=2.0)
        print("mouse: %s" % str(pyautogui.position()))
        break

    if args.command == "bounty" or args.command == "small" or args.command == "medium":
        start_image = "bountysmall.png"
        bounty_size = "small"
        if args.command == "medium" or args.size == "medium":
            bounty_size = "medium"
            start_image = "bountymedium.png"

        print("Buying %s bounties of size %s" % (args.loops, bounty_size))
        # Inventory Region
        region = region_for_screenshot(350, 170, 565, 325)
        try:
            bounty_target = locate(start_image, search_region=region)
        except Exception:
            print("Error: could not find bounty image %s: is the inventory open?" % (start_image))
            sys.exit(1)
        if not bounty_target:
            print("Error: could not find bounty image %s: is the inventory open?" % (start_image))
            sys.exit(1)
        # use offset instead of image find ...
        bar_target = with_top_offset(742, 386, as_point=True)
        go_target = with_top_offset(555, 432, as_point=True)
        while True:
            move_to_menu()
            loops += 1
            print("Buying bounty %d of %d" % (loops, args.loops))
            bounty_target = click_with_position(start_image, bounty_target)
            time.sleep(0.25)
            bar_target = click_with_position("bountybar.png", bar_target)
            time.sleep(0.25)
            go_target = click_with_position("bountygo.png", go_target)
            # drops can take a while to process, give it sec or two
            if loops >= args.loops:
                sys.exit(0)
            time.sleep(1.5)
        sys.exit(0)

    if args.command == "silver" or args.command == "gold":
        mouse_move_speed = 0.5
        time.sleep(mouse_move_speed)
        inventory_target = None
        bar_target = None
        go_target = None
        flip_target = None
        done_target = None
        while True:
            loops += 1
            print("Opening 50 silver chests batch %d of %d" % (loops, args.loops))
            # inventory_target = click_with_position("openinventory.png", inventory_target, 40, 100)
            # move_to_menu()
            # time.sleep(2)
            click_offset(132, 126, duration=mouse_move_speed, delay=0.5)
            # bar_target = click_with_position("bountybar.png", bar_target)
            click_offset(744, 385, duration=mouse_move_speed, delay=0.5)
            # go_target = click_with_position("openopen.png", go_target, click=False)
            delay = 2.5
            if args.command == "gold":
                delay = 4.5
            click_offset(551, 431, duration=mouse_move_speed, delay=delay)
            # flip_target = click_with_position("openflip.png", flip_target)
            click_offset(726, 359, duration=mouse_move_speed, delay=delay)
            # click in same place for show all
            # flip_target = click_with_position("openflip.png", flip_target)
            click_offset(726, 359, duration=mouse_move_speed, delay=2.5)
            # done_target = click_with_position("opendone.png", done_target)

            pyautogui.press("esc")

            # pyautogui.moveRel(300, 0, duration=0.0)
            time.sleep(0.5)
            if loops >= args.loops:
                sys.exit(1)

    while args.command == "testimages":
        level, plus = get_current_zone(level_images, args.save_mismatch)
        if level > 0:
            print("zone found %d, %s, %s" % (level, plus, on_boss()))
        else:
            print("not found")
            
        print("sleeping ... ")
        time.sleep(3.0)

    if args.command == "stack":
        for s in range(args.loops, 0, -1):
            print("===== Stacking: %d to go (charge_time=%d) =====" % (s, args.charge))
            restart_stacking(args)
            if s > 1:
                time.sleep(15.0)
        sys.exit(0)

    if args.command == "testboss":
        time.sleep(2.0)
        is_on_boss = on_boss()
        print("on boss = %s" % is_on_boss)
        sys.exit(0)

    if args.command == "testzone":
        print("Testing zone detection")
        found_app = activate_app(APP_NAME)
        print("%s" % str(found_app))
        print("%d,%d" % (found_app.left, found_app.top))
        print("Configured top_x,top_y = %d,%d" % (top_x, top_y))
        top_x, top_y = found_app.left+1, found_app.top+top_offset
        print("new top_x,top_y = %d,%d" % (top_x, top_y))

        level, plus = get_current_zone(level_images, True, tries=3)
        if level <= 0:
            sys.exit("Cound not find zone, saved in my_screenshot*.png")
        print("Zone found %d (at start zone: %s), (on_boss: %s)" % (level, plus, on_boss()))
        sys.exit(0)

    if args.command == "legacyzone":
        print("Legacy zone detection")
        x, y = get_menu(tries=10)
        region = get_level_region()
        print("%d, %d vs %s" % (x, y, region))
        level, plus = get_current_level(x, y, level_images, args.save_mismatch)
        print("old %s, %s" % (level, plus))
        sys.exit(0)

    if args.command == "modron":
        infinite_loop = True
        # try:
        #     verified = verify_menu(update=False)
        # except Exception:
        #     print("ERROR: Can't verify menu location. Exiting.")
        print("Modron Gem Farming: Briv recharge=%d; modron goal=%d; charge=%f seconds; havi ult=%s; hew ult=%s shandie=%ds" % (
            args.target-args.briv_recharge_areas,
            args.target,
            args.charge, args.havi_ult, args.hew_ult,
            args.charge_shandie
        ))
        print("(Hit CTRL-C to stop or move mouse to the corner of the screen)")
        need_havi_ult = True
        need_recharge = True
        log_restarted = False
        need_leveling = not config.getboolean("idler", "familiar_leveling")
        log_initial = True
        last_level = -1
        now = datetime.datetime.now()
        tracker = Tracker(now=now,
                          zones=args.target,
                          verbose=verbose,)
        last_level_time = now
        while True:
            now = datetime.datetime.now()
            try:
                level, plus = get_current_zone(level_images, args.save_mismatch)
                if verbose:
                    print("Zone found %d (at start zone: %s), (on_boss: %s)" % (level, plus, on_boss()))
            except Exception as e:
                print("Error getting current level: %s" % str(e))
                level = -2
                plus = False
            verbose_print("Level %d" % level)
            if log_initial:
                tracker.start_tracking(now, level, plus)
                log_initial = False
            # check for stalled or hung game
            if last_level == level and level > 0:
                # check delta
                delta = (now - last_level_time).total_seconds()
                if delta > 45:
                    # try 'q' 'g' to see if it unsticks
                    pyautogui.press('q')
                    pyautogui.press('g')
                    pyautogui.press('q')
                if delta > 90:
                    print("Error stuck at zone %s at %s for %d seconds ..." % (level, datetime.datetime.now(), delta))
                    # kill the app and restart
                    shutdown_app(args.keyboard_shutdown)
                    # attempt restart below
                    level = -1
            else:
                last_level = level
                last_level_time = now
            if level <= 0:
                try:
                    verbose_print("Error: is restart needed?")
                    accept_screen_share(args.screenshare)
                    foreground_or_start()
                    # TODO: Need to be able to see if in auto or ran by end zone or ... or maybe if stuck triggered?
                    # time.sleep(1.0)
                    # pyautogui.press("g")

                except Exception as e:
                    print("Error restarting... wait and try again %s" % str(e))
                    time.sleep(10.0)

            elif level == 1 and not plus and log_restarted and args.charge_shandie > 0:
                log_restarted = False
                tracker.start_loop(now, level, plus)
                print("Loop started %s: %d (charging shandie for %d seconds)" % (datetime.datetime.now(), level, args.charge_shandie))
                pyautogui.press("g")
                for i in range(0,20):
                    pyautogui.press("f6")
                time.sleep(args.charge_shandie)
                foreground_or_start()
                pyautogui.press("g")
                time.sleep(2.0)
            elif level == 1 and need_leveling:
                if log_restarted:
                    log_restarted = False
                    tracker.start_loop(now, level, plus)
                    print("Loop started %s: %d" % (datetime.datetime.now(), level))
                # Manual leveling
                level_team_with_keys(args, speed_team, between_champs=DEFAULT_DELAY)
                need_leveling = False
                need_recharge = True
            elif level < 40 and need_havi_ult:
                need_recharge = True
                if log_restarted:
                    tracker.start_loop(now, level, plus)
                    log_restarted = False
                if level >= 11:
                    need_havi_ult = False
                    print("Havi Ult")
                    for i in range(0,40):
                        pyautogui.press(args.havi_ult)
                        time.sleep(0.1)
                time.sleep(1.0)
            elif level < args.target - 100:
                diff = args.target - level
                if args.briv_boss:
                    # foreground_or_start()
                    debug_print("checking for team on_boss")
                    if on_boss():
                        verbose_print("team is on_boss")
                        pyautogui.press('e')
                        pyautogui.press('g')
                        while on_boss():
                            pass
                        pyautogui.press('q')
                        time.sleep(0.5)
                        pyautogui.press('g')
                        time.sleep(0.5)
                        pyautogui.press('q')
                    if args.screenshare:
                        accept_screen_share(args.screenshare)
                else:
                    time.sleep(diff*1.0)
                    foreground_or_start()
            elif level < args.target - args.briv_recharge_areas:
                continue
            else:
                log_restarted = True
                if need_recharge:
                    charge_briv(level, plus, level_images, args)
                    last_level = -1
                    last_level_time = datetime.datetime.now()
                    verbose_print("Recharge finished: %s" % last_level_time)
                    need_recharge = False
                need_havi_ult = True
                time.sleep(1.0)

    OFFSET_xx2 = 1925 - OFFSET_xx1
    OFFSET_xx3 = 2025 - OFFSET_xx1
    OFFSET_xx4 = 2122 - OFFSET_xx1
    if args.command == "grab":
        region = get_level_region()
        raw_im = pyautogui.screenshot(region=region)
        im = raw_im.convert('RGB')
        im.save("1xx.png")
        sys.exit(0)
        x, y = menu_location()
        pyautogui.moveTo(x, y)
        x, y = location_for_screenshot(440, 240)
        region = region_for_screenshot(350, 170, 565, 325)
        im = pyautogui.screenshot(region=region)
        im.save("inventory.png")
        sys.exit(0)
        level, plus = get_current_zone(level_images, args.save_mismatch)
        # x, y = get_menu()
        print("x = %f y = %f" % (x, y))
        # x01
        # x = menu_home.x * 2 + 1830
        # y = menu_home.y * 2 + 10
        im = pyautogui.screenshot(region=(x, y, IMAGE_WIDTH, IMAGE_HEIGHT))
        im.save("1xx.png")
        # x02
        # x = menu_home.x * 2 + 1927
        im = pyautogui.screenshot(region=(x+OFFSET_xx2, y, IMAGE_WIDTH, IMAGE_HEIGHT))
        im.save("2xx.png")
        # x03
        # x = menu_home.x * 2 + 2025
        im = pyautogui.screenshot(region=(x+OFFSET_xx3, y, IMAGE_WIDTH, IMAGE_HEIGHT))
        im.save("3xx.png")
        # x04
        # x = menu_home.x * 2 + 2122
        im = pyautogui.screenshot(region=(x+OFFSET_xx4, y, IMAGE_WIDTH, IMAGE_HEIGHT))
        im.save("4xx.png")
        # boss
        # x = menu_home.x * 2 + 2219
        # im = pyautogui.screenshot(region=(x, y, 56, 56))
        # im.save("boss.png")
        sys.exit(1)

    while args.command == "monitor":
        time.sleep(1.0)
        menu_home = locate('menu.png')
        print("menu_home.x = %f menu_home.y = %f" % (menu_home.x, menu_home.y))
        x = menu_home.x * 2 + 1830
        y = menu_home.y * 2 + 10
        # Try grabbing a small section of screen
        for i in range(0,300):
            time.sleep(5)
            im = pyautogui.screenshot(region=(x, y, IMAGE_WIDTH, IMAGE_HEIGHT))
            # in list?
            found = False
            for name, img in level_images.items():
                diff = ImageChops.difference(im.convert('RGB'), img).getbbox()
                if not diff:
                    try:
                        level = int(name[7:10])
                    except Exception:
                        level = 0
                    print("Found %s again %s" % (name, level))
                    found = True
                    break
            if found:
                continue

            print("Saving %i" % i)
            im.save('my_screenshot%d.png' % i)
            
        break

    if args.command == "move":
        x = args.loops
        y = args.extras[0]
        found_app = activate_app(APP_NAME)
        rect = found_app._rect
        print("app=%s" % str(found_app))
        sys.exit(0)
        # click_second_spec(delay=1.0)

    while args.command == "press":
        keys = ["q", "w", "e"]
        print("Pressing %s" % keys[args.loops-1])
        pyautogui.press(keys[args.loops-1])
        time.sleep(10)
        # click_second_spec(delay=1.0)

    while args.command == "buy":
        found = click_image("1chest.png", "1chestH.png", delay=0.5)
        time.sleep(0.25)
        while found:
            pyautogui.moveRel(900, 0, duration=0.0)
            time.sleep(0.25)
            pyautogui.click()
            loops += 1
            if loops >= args.loops:
                break
            time.sleep(2.5)
            pyautogui.moveRel(-900, 0, duration=0.0)
            time.sleep(0.25)
            pyautogui.click()
            time.sleep(0.25)
        if loops >= args.loops:
            break

    start_time = datetime.datetime.now()
    do_startup = True
    if args.in_progress:
        do_startup = False
    wait_minutes = 10 if args.loops == 0 else args.loops
    while args.command in no_modron_commands:
        infinite_loop = True
        loop_time = datetime.datetime.now()
        menu_home = None
        ult = 0
        loops += 1
        if loops > args.runloops:
            break

        print("Starting loop %d at %s" % (loops, datetime.datetime.now()))
        if do_startup:
            # Startup by clicking on the Mad Wizard City
            start_it_up(args.adventure)
            for i in range(0, 20):
                time.sleep(1.0)
                blue, grey = check_for_menu()
                if blue or grey:
                    break

            # We are now on Level 1: Time to GO
            # Drop Fams First
            print("Dropping up to %d Familiars" % (args.familiars,))
            time.sleep(DEFAULT_DELAY)
            pyautogui.press('g')
            time.sleep(DEFAULT_DELAY)
            # Now we have formations!
            # place_click_familiars(args.familiars)
            pyautogui.press('q')
            time.sleep(DEFAULT_DELAY)

            # Level Champs
            print("Leveling up Champs")
            level_team_with_keys(args, speed_team, between_champs=DEFAULT_DELAY)

            print("Running for %d minutes before checking for Briv Charging %s" % (args.loops, datetime.datetime.now()))
            for m in range(wait_minutes, 0, -1):
                print("  %d minutes" % m)
                time.sleep(60.0)

        do_startup = True

        # check the level and charge Briv
        # recharge Briv
        if have_briv:
            while True:
                try:
                    time.sleep(10)
                    level, plus = get_current_zone(level_images, args.save_mismatch)
                    if level >= args.target:
                        charge_briv(level, plus, level_images, args)
                        break
                except Exception as a:
                    print("Briv Charge Error: %s" % str(a))
                    pass

        # shutdown the loop
        print("Wrapping up starting at %s" % (datetime.datetime.now()))
        try:
            wrap_it_up()
        except Exception as a:
            print("Wrap Up Error: %s" % str(a))
            pass

        # dump some stats
        run_time = datetime.datetime.now() - start_time
        loop_time = datetime.datetime.now() - loop_time
        print("Loops: %d Runtime: %s This Loop: %s Average Loop: %s Crashes: %d" % (
            loops,
            run_time,
            loop_time,
            run_time / float(loops),
            crashes)
        )

    # print("%s" % list(pyautogui.locateAllOnScreen('./burger2.png')))

if __name__ == "__main__":
    first_loop = True
    while first_loop or infinite_loop:
        try:
            main_method()
        except Exception as e:
            print("WARNING: exception caught: %s" % e)
