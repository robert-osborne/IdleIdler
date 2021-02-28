# IdleIdler

    TODO:
    [ ] Explain how it works better (what to expect)
    [ ] Screen shots of my teams
    [ ] Clean up the choices and make them copies
    [ ] Explain don't need team defined for modron + fams
    [ ] Test and debug leveling with out fams and without modron and update documenation

Warning: Use at own risk, this script uses a development environment and controls game play in a way that can go wrong.  The author makes no warranties this will work for you.

A python script for automating [Idle Champions](http://www.idlechampions.com/) on Mac OS.  Runs very stable when using Modron with lots of familiars.   Can also script in a reasonably stable manner with fewer familiars with or without Modron automation.

The Author is is currently getting about 320 Bosses Per Hour (BPH) with 99% triple skip Briv.  Your mileage, or BPH, may vary.

Has some additional goodies:

1. Opening small or medium bounty contracts or silver chests in batches
1. Calculating item levels in blacksmith contracts
1. Calculating number of event free plays from bounty contracts
1. Calculating the number of briv skips from steelskin stacks.

## Cavets and Issues

1. Idler requires the game be in focus.  The script will bring the app to the foreground when needed (which is a lot).  This may mean that it runs mostly overnight for you (I have an old mac I run Idle Champions on)
2. Idler uses image matching and saved, app must be configured using Resolution 1280x720 and UI Scale 100%
2. Idler has not been tested on Big Sur (I haven't upgraded yet).
2. The Idle Champions app can't be moved from it's default screen and location.
2. Idler is a hack project that has been cobbled together piecemeal in my spare time.  Please don't judge my programming based on this :-)

## Installation

This all runs within the Mac OS X terminal application:

1. Give the terminal app ![accessibility permissions](documentation/accessibility.md) 
1. Install python3 in a virtualenv, I personally use [homebrew](https://brew.sh/). There are number of guides available for doing this, for instance [this one](https://www.studytonight.com/post/python-virtual-environment-setup-on-mac-osx-easiest-way)
1. Download or git clone this repository.
1. Inside the virtualenv you created above,  load the requirements:

        pip install -r requirements.txt

1. Test

        ./idler.py stats
    
1. Start up Steam and [create a desktop shortcut](documentation/AddDesktopShortcut.png) for Idle Champions.  If this short cut doesn't work you may need to repair it:

        ./idler.py repair_shortcut
        
1. Start up Idle Champions. Now test if the script can detect the current zone:

        ./idler.py zone
        
    this should bring Idle Champions to the foreground and print something like:
    
        Looking for the Idle CHampions app
        Zone found 216 (at start zone: False), (on_boss: False)
        
1. If that works, the rest should be good to go.

***

# Gem Farming

## Introduction

The main reason to use a script for gem farming is to "recharge" Briv at the end of every run, something Modron Automation can't do.

The second reason is if you are a new player and don't yet have Modron Automation but want to build up gems overnight or during other times youa are away from your computer.

Both methods are covered below.

#### Choose your method of gem farming:

1. Modron Automation with lots of familiars.  This is the most stable but assumes enough familiars to level all champs and maximise click damage and pick.  At least 15 familiars for optimal speed team.
2. Modron Automation with 4 or 6 familiars.  This method uses a minimum number of familiars and gets good speed.  It can be more finicky to set up.
3. No modron automation with 2, 4 or 6 familiars.   For new players who may want to run gem farming overnight while trying to build up to buy their first core.

#### Follow the setup instructions below for your chosen method!

---

## Modron Automation with lots of familiars 

### Getting Started and What to Expect

You set up modron automation (MA) with a speed team and clickers being leveled up with familiars.  Then you use IdleIlder to "catch" the speed team just before MA resets and it swaps in a "charge" team to recharge Briv.

IdleIdler uses the saved formations to accomplish the team swapping for charging Briv.





### Setting Up Formation

Formation 1 (q): speed team, 5 or 6 familiars on battlefield, one familiar on click
leveling and all your champs, one familiar on Hew's ULT, save with the speed
specializations chosen (my current speed team is here).  The author's team look like this.

Formation 2 (w): recharge team: Briv at front, if your click wall is high
enough you can also have Sentry and/or Melf in this team as well.  The author's charging team (for reset zones over 400) looks like this:

# Modron Automation with 4 or 6 familiars

# No modron automation with 2, 4 or 6 familiars 
#### 1. For new players gem farming is currently best done using the Mad Wizard free play but other free plays may work better for your speed team.
#### 2. Set up your Mad Wizard saved formations depending which form of gem farming you are going to do


##### 2.1 Modron with lots of familiars


##### 2.2 Modron with 4 or 6 familiars

Formation 1 (q): speed team, 3 or 5 familiars on battlefield, one familiar on click leveling, save with specializations chosen

Formation 2 (w): recharge team: Briv at front, if your click wall is high enough you can also have Sentry and/or Melf in this team as well

#### 2.3 No Modron, 4 or 6 familiars 

Formation 1 (q): speed team, 3 or 5 familiars on battlefield, 1 familiar on click leveling, save with specializations chosen

Formation 2 (w): recharge team: Briv at front, if your click wall is high enough you can also have Sentry and/or Melf in this team as well

### 3. Copy the appropriate sample config to local.cfg

Modron core with lots of familiars:

        cp sample_config_modron_familiars.cfg local.cfg
        
Modron core with 4 or 6 familiars:

        cp sample_config_modron_fkey_leveling.cfg local.cfg
        
No Modro core (4 or 6 familiars recommended, 2 minimum):

        cp sample_config_no_modron.cfg local.cfg
        
### 4. Update local.cfg using the rest of these instructions

### 5. Configure your highest click level or "click wall"

Let your speed team run until it slows down because the click damage is no longer instantly killing the spawning monsters.  That is your click wall.  Pick the largest number that ends with a 30 or 80, that is your click target (you get more BPH by running to one of those levels)

        [idler]
        # set modron automation [Set Goal Area] to 330
        modron_target = 330
        
### 5. Choose Reset Charge vs. Wait Recharge

Reset Charge gives better BPH but is slightly more unreliable.  Wait Recharge is more reliable but the app spends a few extra minutes at the end of each cycle to recharge Briv.

        [idler]
        briv_restart_charging = yes
        briv_charge_time = 15.0

or

        [idler]
        briv_restart_charging = no
        # Charge time is dependent upon click wall
        briv_charge_time = 150.0

### 7. Configure your speed team

        [idler]
        # Current list of acceptable champs:
        # briv,shandie,havi,deekin,melf,sentry,hew,viper,binwin,drizzt,minsc,strix,hitch
        # Limit of 9 champs.
        speed_team = shandie,briv,drizzt,sentry,havi,deekin,hew,melf,binwin
        hew_ult=6
        havi_ult=8
        
### 8. Gem Farm

        ./idler.py modron

#### What to expect

    The authors gem farming 

## Advanced Topics

Coming soon:  how to "farm" patrons with a modified speed team.

## Additional Commands

2. Buying bounties quickly, the following commands will by 50 bounties of the given type (the inventory screen must be open)

        ./idler.py small 5
        ./idler.py medium 5

3. Opening silver chests quickly, the following command will open 5 batches of 50 silver chests (the chest opening screen must be open)

        ./idler.py silver 5

4. Quick restart stacking, assuming Briv is at a level where he can no longer advance:

        ./idler.py --charge 15 stack 5
        
## Todo

    # TODO: things on my todo list
    # [ ] Tracking stats like BPH and average loop duration
    # [ ] Recharge briv by swapping to the background team instead of restarting
    # [ ] Flag to pause on level 1 and allow Shandie's dash to reset
    # [ ] Flag to do briv swapping at each zone complete (heavy duty and occupies entire time)
    # [ ] Make champ flags work so don't need team in config file or can modify team in config file (for chores)
    # [ ] Add more champs to the familiar leveling code
    # [ ] Level Shandie and then wait for dash to trigger
    
