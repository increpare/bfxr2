"""Conservative, metadata-only UCS indexing for four described SFX collections.

Run with --root, --ucs and --output. Never changes original media. Confidence
describes the metadata-to-taxonomy mapping, not audio verification or suitability
for training. Broad categories intentionally have no invented MISC leaf.
"""
import argparse
import collections
import json
from pathlib import Path
import re

LIBRARIES = ['BBC', 'HB01 - Hanna-Barbera Sound FX Library', 'Hanna-Barbera Sound FX Library',
             'valentinosoundeffectslibrary', 'rpgmaker2k', 'PaRappa TV Anime-Animation Sound FX']
AUDIO = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif', '.m4a'}

# These are exact observed filename families, not substring/synonym expansion.
HB = {}
def hb(catid, names):
    HB.update({name: catid for name in names.split()})

hb('TOONBoing', 'BoingCartoon BoinkCartoon BounceCartoon SpringCartoon')
hb('TOONImpt', 'HitCartoon CrashCartoon SlapCartoon')
hb('TOONImpt', 'ThudCartoon ThumpCartoon ZonkCartoon')
hb('TOONHorn', 'HornCartoon')
hb('TOONMx', 'BugleCartoon DrumsCartoon KazooCartoon PianoCartoon')
hb('TOONMx', 'TrumpetCartoon')
hb('TOONPluk', 'PluckCartoon')
hb('TOONPop', 'PopCartoon')
hb('TOONShake', 'ShakeCartoon HeadShakeCartoon RattleCartoon')
hb('TOONSplt', 'SplatCartoon')
hb('TOONSqk', 'SqueakCartoon')
hb('TOONStrch', 'StretchCartoon')
hb('TOONSwsh', 'SwishCartoon SwooshCartoon')
hb('TOONTwang', 'TwangCartoon')
hb('TOONZip', 'ZipCartoon')
hb('ANMLRept', 'Alligator Crocodile')
hb('ANMLPrim', 'Ape Chimpanzee Gorilla Monkey')
hb('ANMLWild', 'Anteater Badger Bear Elephant Hippopotamus Hyena Rhinoceros')
hb('ANMLBat', 'Bat')
hb('ANMLInsc', 'Bees Cricket Fly')
hb('ANMLCat', 'Cat')
hb('ANMLWcat', 'Cougar Leopard Lion Tiger')
hb('ANMLFarm', 'Cow Goat Lamb Pig Sheep')
hb('ANMLWdog', 'Coyote Wolf')
hb('ANMLDog', 'Dog')
hb('ANMLHors', 'Donkey Horse')
hb('ANMLAmph', 'Frog')
hb('ANMLRdnt', 'Rat Squirrel')
hb('ANMLAqua', 'Seal')
hb('BIRDSong', 'BirdBluebird BirdMeadowlark')
hb('BIRDPrey', 'BirdBuzzard BirdHawk BirdOwl')
hb('BIRDFowl', 'BirdChicken BirdDuck BirdGoose BirdRooster BirdTurkey')
hb('BIRDTrop', 'BirdCockatoo BirdParrot BirdToucan')
hb('BIRDWade', 'BirdCrane')
hb('BIRDCrow', 'BirdCrow')
hb('OBJCoin', 'CoinBag CoinDrop CoinFlip CoinHit CoinPour CoinRustle CoinScoop CoinSpin')
hb('BELLLrg', 'BellBig')
hb('BELLGong', 'Gong')
hb('MUSCBell', 'BellOrchestra')
hb('ALRMBell', 'BellSchool')
hb('CLOCKTick', 'ClockTick')
hb('GLASCrsh', 'CrashBottle CrashGlass SmashGlass')
hb('WOODBrk', 'BreakBranch SnapWood')
hb('WOODCrsh', 'CrashWood CrashTree')
hb('WOODFric', 'CreakWood')
hb('WOODImpt', 'HitWood DropWood')
hb('METLCrsh', 'CrashMetal CrashCans')
hb('METLImpt', 'HitMetal DropCan')
hb('METLFric', 'ScrapeMetal')
hb('ROCKCrsh', 'CrashBrick CrashStone')
hb('ROCKFric', 'ScrapeRock')
hb('CERMCrsh', 'SmashDishes SmashPottery')
hb('DOORWood', 'DoorWood')
hb('DOORMetl', 'DoorMetal')
hb('DOORSwng', 'DoorSaloon')
hb('DOORHdwr', 'DoorKnob DoorKnocker')
hb('DOORKnck', 'KnockDoor')
hb('WNDWKnck', 'KnockWindow')
hb('FOODIngr', 'CrackNut EggCrack SmashMelon')
hb('FOODKware', 'CanSoftDrink')
hb('OBJFurn', 'CreakChair')
hb('MACHOffc', 'CashRegister')
hb('GUNHndl', 'GunHandFoley GunRifleFoley GunHolster')
hb('GUNPis', 'GunHandGun')
hb('GUNRif', 'GunRifle')
hb('GUNAuto', 'GunMachineGun')
hb('GUNShotg', 'GunShotGun')
hb('BLLTRico', 'Ricochet')
hb('FGHTBf', 'FallBody')
hb('FGHTImpt', 'HitHuman')
hb('VEHSkid', 'SkidAuto')
hb('FIREIgn', 'Match')
hb('GEOLava', 'BubbleLava')
hb('LIQBubl', 'BubbleMud')
hb('WATRBubl', 'BubblesWater')
hb('WATRSplsh', 'CrashWater')
hb('WATRSplsh', 'WaterSplash')
hb('WATRDrip', 'WaterDrip')
hb('WATRFlow', 'WaterFlow')
hb('WATRMvmt', 'WaterSwimming')
hb('WATRUndwtr', 'WaterUnderwater')
hb('WATRPlmb', 'Toilet')
hb('ROPECreak', 'StretchRope')
hb('COMType', 'Typewriter')
hb('MUSCTnprc', 'Xylophone')
hb('AEROProp', 'AirplaneProp')
hb('SPRTCourt', 'Basketball Tennis')
hb('MUSCBell', 'BellSleigh')
hb('MUSCChim', 'Chimes')
hb('ANMLInsc', 'Cicadas')
hb('CRWDAngr', 'CrowdAngry')
hb('CRWDChld', 'CrowdChildren')
hb('FIREBrst', 'FireFlameThrower')
hb('TOONHorn', 'HornBulb')
hb('HORNAir', 'HornFog')
hb('MECHRtch', 'Ratchet')
hb('TOOLHand', 'Scissors')
hb('HMNSnor', 'SnoreFemale SnoreMale')
hb('AMBSwmp', 'SwampAmbience')
hb('AMBTraf', 'TrafficCity')
hb('ANMLAqua', 'Whale')
hb('WHSTMech', 'WhistleSteam')
hb('WIND', 'Wind')
hb('ICEImpt', 'DropIce')
hb('ROPEImpt', 'DropRope')
hb('COMPhono', 'RecordPlayer RecordScratch')
hb('EQUIPRec', 'FishingReel')
hb('SPRTIndor', 'PoolBilliards CrashBowling')
hb('SPRTWntr', 'FallSki')
hb('SNOWMvmt', 'RollSnowball')
hb('FEETHmn', 'SpursFootsteps')
# Additional literal families reviewed against the supplied leaf definitions.
# Cartoon source/type names can establish a leaf without claiming a real source.
hb('TOONAnml', 'BirdCartoon DinosaurCartoon DogCartoon HorseCartoon MosquitoCartoon WoodpeckerCartoon')
hb('TOONVox', 'GrowlCartoon GruntCartoon GulpCartoon LaughterCartoon SnoreCartoon VoiceCartoon WhineCartoon RazzberryCartoon')
hb('TOONVeh', 'AutoCartoon RickshawCartoon')
hb('TOONMach', 'MachineCartoon')
hb('TOONZip', 'ZoomCartoon')
hb('CREAEthr', 'Banshee')
hb('CREAMnstr', 'Monster')
hb('AMBFarm', 'Barnyard')
hb('AMBWar', 'BattleMilitary BattleWestern')
hb('BELLAnml', 'BellCowbell')
hb('BIRDMisc', 'BirdPigeon BirdWoodpecker')
hb('BIRDTrop', 'BirdsJungle')
hb('BOATMech', 'CreakShip')
hb('BOATRow', 'WaterRow')
hb('COMCam', 'Camera')
hb('DESTRCrsh', 'CrashAuto CrashGarbage FallDebris')
hb('DIRTMvmt', 'ScrapeDirt')
hb('GAMEArcd', 'Pinball')
hb('MACHElev', 'DoorElevator')
hb('MUSCWind', 'MusicBagpipes')
hb('MUSCPerc', 'MusicPercussion')
hb('AEROMech', 'SwitchCockpit')
hb('ALRMSirn', 'Siren')
hb('TOOLHand', 'Axe')
hb('VEHWagn', 'Wagon')
# HB04 is present in the library but was absent from the earlier generated
# labels. Its literal sources are independently described by their filenames.
hb('TOONVeh', 'AirplaneCartoon HelicopterCartoon MotorcycleCartoon TrainCartoon')
hb('TOONMach', 'MotorCartoon PumpCartoon PressCartoon ComputerCartoon PileDriverCartoon WashingMachCartoon')
hb('TOONVox', 'KissCartoon ChewCartoon LaughCartoon SlurpCartoon')
hb('AEROJet', 'AirplaneJet')
hb('AEROHeli', 'Helicopter')
hb('VEHAntq', 'AutoAntique AutoVintage')
hb('VEHCar', 'AutoVolkswagen AutoBackfire')
hb('VEHDoor', 'AutoDoor')
hb('VEHBrake', 'AutoBrake')
hb('VEHMech', 'AutoGears')
hb('VEHRace', 'AutoRaceDragster')
hb('VEHSkid', 'AutoSkid AutoTireSqueal')
hb('VEHMoto', 'Motorcycle')
hb('BOATMotr', 'BoatJet BoatOutboard')
hb('BOATShip', 'Ship')
hb('BOATSub', 'SubmarineMotor')
hb('COMCam', 'CameraMovie')
hb('COMAv', 'ProjectorFilm')
hb('COMTelm', 'Teletype')
hb('MACHCnst', 'CementMixer')
hb('MACHInd', 'MotorGenerator')
hb('CRWDPanic', 'CrowdPanic')
hb('TOOLPneu', 'JackHammer')
hb('TOOLPowr', 'ImpactWrench')
hb('MECHPuly', 'Pulley Winch')
hb('MACHPump', 'PumpHand')
hb('TRNDiesl', 'TrainDiesel')
hb('TRNSteam', 'TrainSteam')
hb('WHSTMech', 'TrainWhistle')
hb('VOXScrm', 'Scream')
hb('PLASHndl', 'RustleFilm')
HB.update({'Roller Coaster':'MACHAmus', 'ShipEngine Room':'BOATInt'})
HB_BROAD = {'Air':'AIR', 'Axe':'TOOLS', 'Balloon':'RUBBER',
            'AirplaneSquadron':'AIRCRAFT', 'BellBrass':'BELLS', 'Camera':'COMMUNICATIONS',
            'CrowdRestless':'CROWDS', 'DoorElevator':'DOORS', 'Electricity':'ELECTRICITY',
            'Camel':'ANIMALS', 'Llama':'ANIMALS',
            'Magic':'MAGIC', 'MusicBagpipes':'MUSICAL', 'MusicPercussion':'MUSICAL',
            'Pinball':'GAMES', 'RumbleVolcano':'GEOTHERMAL', 'SciFi':'SCIFI',
            'ScrapeDirt':'DIRT & SAND', 'Siren':'ALARMS', 'SwitchCockpit':'AIRCRAFT',
            'Train':'TRAINS', 'Wagon':'VEHICLES',
            'BellCowbell':'BELLS', 'BellFight':'BELLS',
            'Barnyard':'AMBIENCE', 'BirdColumbia':'BIRDS', 'BirdPigeon':'BIRDS',
            'BirdWoodpecker':'BIRDS', 'BirdsJungle':'BIRDS', 'BirdsVarious':'BIRDS',
            'Monster':'CREATURES', 'Steam':'AIR', 'Tennis':'SPORTS',
            'WaterRow':'WATER',
            'BattleMilitary':'AMBIENCE', 'BattleWestern':'AMBIENCE',
            'CrashAuto':'DESTRUCTION', 'CrashDoor':'DOORS',
            'CrashGarbage':'DESTRUCTION', 'CrashMeteor':'DESTRUCTION',
            'CreakShip':'BOATS', 'DropGolf':'SPORTS', 'Explosion':'EXPLOSIONS',
            'FallDebris':'DESTRUCTION', 'Fart':'FARTS',
            'GunShootingGaller':'GUNS', 'Pour':None,
            'CuckooWhistle':'WHISTLES'}
HB_BROAD.update({'AirplaneModel':'AIRCRAFT', 'BoatPaddlewheel':'BOATS',
                 'Jeep':'VEHICLES', 'FootstepsWood':'FOOTSTEPS',
                 'Grinder':'TOOLS', 'RobotMotor':'ROBOTS',
                 'TrainRumble':'TRAINS', 'Windmill':'MACHINES'})

# A category title alone is not acoustic evidence. Only clear literal sources
# get leaves; ambiguous action/status names remain reviewable with game_function.
RPG = {'Bell':(None,'BELLS'), 'Bow':('WEAPBow',None),
       'Buzzer':('ALRMBuzr',None), 'Cat':('ANMLCat',None),
       'Chicken':('BIRDFowl',None), 'Clock':(None,'CLOCKS'),
       'Cow':('ANMLFarm',None), 'Dog':('ANMLDog',None),
       'Earthquake':('NATDQuak',None), 'Explosion':(None,'EXPLOSIONS'),
       'Glass':(None,'GLASS'), 'Horse':('ANMLHors',None),
       'Lion':('ANMLWcat',None), 'Monster':('CREAMnstr',None),
       'Rain':('RAIN',None), 'Refer Book':('OBJBook',None),
       'Sheep':('ANMLFarm',None), 'Sword':('WEAPSwrd',None),
       'Thunder':('THUN',None), 'Tiger':('ANMLWcat',None),
       'Water':(None,'WATER'), 'Wind':('WIND',None),
       'Cursor':(None,'USER INTERFACE'), 'Cansel':(None,'USER INTERFACE'),
       'Decision':(None,'USER INTERFACE')}
# Explicit game events/statuses establish the role of a designed videogame
# cue without asserting a physical recording or spelling out a spell source.
# Generic objects, opaque terms and environmental theme words remain outside
# this list; existing literal source mappings above take precedence.
RPG_EVENTS = set('Absorption Annihilation Attack Barrier Bite Blow Close Damage Down Escape Evasion Failure Fall Fight Item Jump Kill Movement Numbness Open Poison Power Rebirth Recovery Shot Silence Sleep Success Teleport Up'.split())
RPG.update({event:('GAMEVideo',None) for event in RPG_EVENTS})
RPG.update({'Flame':(None,'FIRE'), 'Sea':(None,'WATER'),
            'Sand Storm':('STORM',None), 'Song':(None,'MUSICAL'),
            'Switch':('MECHSwtch',None)})
# Abstract holy/dark/cold themes are proposed as magic in this RPG-effect
# collection. The supplied taxonomy explicitly names holy, dark and ice magic.
# This is an intended-theme interpretation, not a claimed acoustic source.
RPG_MAGIC = {'Holy':'MAGAngl', 'Dark':'MAGEvil', 'Darkness':'MAGEvil', 'Cold':'MAGElem', 'Earth':'MAGElem'}
RPG.update({theme:(catid,None) for theme,catid in RPG_MAGIC.items()})

# Specific ordered phrases from the actual descriptions. Category fallback is
# used when a source is known but its sound-producing action is not described.
RULES = [
 (r'\bvelcro\b.*\bopen\b', 'CLOTHRip'),
 (r'\btea pot whistling\b', 'WHSTMech'),
 (r'^electric sign.*letter flips', 'MECHRelay'),
 (r'^pump.*tire.*hand held|^water pump siphon', 'MACHPump'),
 (r'^compressor.*air', 'MACHPump'),
 (r'\bphoton gun|\bfusion(?: ray)?\b', 'SCIWeap'),
 (r'\blight beam hits?\b', 'LASRImpt'), (r'\blaser beam\b','LASRBeam'),
 (r'\bspace (?:vehicle|launch)|\bmother ship\b','SCIShip'),
 (r'\blaser modulations\b','LASRMisc'),
 (r'\bwhoosh\b','WHSH'),
 (r'\btelephone|\btelephones\b','COMTelph'),
 (r'\btelemetry\b','COMTelm'), (r'\bteletype\b','COMTelm'),
 (r'\btypewriter|\btyping \(selectric\)','COMType'),
 (r'\bradio.{0,4}police\b','COMTran'),
 (r'\bfootsteps\b|\bwalking.{0,4}man\b|\bmen marching\b','FEETHmn'),
 (r'\bhorse[s]?\b.*\b(?:walking|walk|walks|canters|trotting|trot|gallop|canter|passes|passing|approaches.*gravel)\b','FEETHors'),
 (r'\bhorsedrawn gun carriage|\bwagon.{0,4}horse drawn','VEHWagn'),
 (r'\bhorse[s]?\b|\bdonkey[s]?\b','ANMLHors'),
 (r'\b(?:cat|cats)\b|\bcat.{0,4}meow','ANMLCat'),
 (r'\bdogs?\b|\bbeagle\b|\blabrador\b','ANMLDog'),
 (r'\b(?:tiger|lion|cougar)\b','ANMLWcat'),
 (r'\b(?:piglets?|pigs?|sow|cows?|calves|cattle|sheep|rams?|bull|heifers)\b','ANMLFarm'),
 (r'\b(?:gorilla|monkey)\b','ANMLPrim'),
 (r'\brattlesnake\b','ANMLRept'), (r'\belephant\b','ANMLWild'),
 (r'\b(?:chickens?|cock crows|hen|ducks?|geese|goose|shelduck|garganey|wildfowl|peacock)\b','BIRDFowl'),
 (r'\b(?:flamingoes|coot|moorhen)\b','BIRDWade'),
 (r'\b(?:lory|parakeet|cockatoos)\b','BIRDTrop'),
 (r'\b(?:owl|vulture)\b','BIRDPrey'), (r'\bcrow\b','BIRDCrow'),
 (r'\b(?:canary|meadowlark|robin)\b','BIRDSong'),
 (r'\b(?:crickets|locust)\b','ANMLInsc'),
 (r'\b(?:baby|babies)\b','VOXBaby'),
 (r'\bcoughing\b','HMNCough'), (r'\bsneezing\b','HMNSneez'),
 (r'\b(?:crying|sobbing)\b','VOXCry'),
 (r'\b(?:laughing|giggling)\b','VOXLaff'),
 (r'\bscreaming\b','VOXScrm'), (r'\b(?:belching|burping)\b','HMNBurp'),
 (r'\b(?:sighing|heavy breathing)\b','HMNBrth'),
 (r'\bkiss\b','HMNKiss'), (r'\bmoaning\b','VOXEfrt'),
 (r'\bsnoring\b','HMNSnor'), (r'\bheart ?beat\b','HMNHart'),
 (r'\bapplause\b','CRWDApls'), (r'\bwalla\b','CRWDWalla'),
 (r'\bthunder storm\b','STORM'), (r'\bthunder\b','THUN'),
 (r'^rain\b','RAIN'), (r'^wind\b','WIND'),
 (r'\bwaterfalls?\b|\bniagra falls\b','WATRFall'),
 (r'\briver with rapids\b','WATRTurb'),
 (r'\b(?:brook|stream|river)\b','WATRFlow'),
 (r'\bsurf.{0,4}ocean\b','WATRSurf'),
 (r'\bwaves against boat\b','BOATWash'),
 (r'\bwater.{0,4}(?:wash|runs in sink)|\btoilet flush|\bshower.{0,4}on','WATRPlmb'),
 (r'\blawn sprinkler\b','WATRSpray'),
 (r'\baerosol can spray\b','AIRBlow'),
 (r'\bgas canister being emptied\b|\btire.{0,4}deflating\b','AIRHiss'),
 (r'\bice cracking\b','ICEBrk'),
 (r'\bice into\b','ICEImpt'),
 (r'\b(?:soda|beer|water|tea).{0,6}pour|\bpoured into (?:glass|cup)\b','FOODPour'),
 (r'\bwine glasses in toast\b|\bglass.{0,4}tea cup\b','FOODGware'),
 (r'\bpotato chip crunch\b','FOODEat'),
 (r'\begg break\b|\bbeating eggs\b','FOODIngr'),
 (r'\bfrying sizzle\b','FOODCook'),
 (r'\bpots and pans\b','FOODKware'),
 (r'\bdish(?:ware)?(?: clinks|.{0,4}clinks)|\bsilverware\b','FOODTware'),
 (r'\bglass.{0,15}break|\bwindow.{0,10}break','GLASBrk'),
 (r'\b(?:glass.{0,4}small bottle|mason jar|liqueur bottle)\b','GLASHndl'),
 (r'\bdoor.{0,8}bell\b|\bdoor entrance\b','BELLDoor'),
 (r'\bchurch bells?\b','BELLLrg'),
 (r'\bbells?.{0,8}hand\b','BELLHand'), (r'\bgong\b','BELLGong'),
 (r'\b(?:sleigh bells|bell.{0,4}sleigh|bells.{0,4}xmas)\b','MUSCBell'),
 (r'\bbell.{0,6}train crossing\b','ALRMBell'),
 (r'\balarm.{0,4}smoke\b','ALRMElec'),
 (r'\balarm clock.{0,4}bell\b','ALRMClok'),
 (r'\bclock\b.*\b(?:ticks?|ticking)\b','CLOCKTick'),
 (r'\bclock\b.*\b(?:toll|tolling|chimes?|striking)\b|anne boleyn.*o_clock','CLOCKChim'),
 (r'\bclock\b.*\b(?:winding|wind-up|mechanism)\b','CLOCKMech'),
 (r'\b(?:bugle|orchestra)\b','MUSCPrfm'),
 (r'\btambourine\b','MUSCShake'), (r'\bcymbal\b','MUSCPerc'),
 (r'\bmachine gun\b','GUNAuto'),
 (r'\bshot ?gun\b','GUNShotg'), (r'\bpistol\b','GUNPis'),
 (r'\brifle shots\b','GUNRif'), (r'\bcannon fire\b','GUNCano'),
 (r'\bwhip\b','WEAPWhip'),
 (r'\bblow torch\b','FIRETrch'), (r'\bfireplace\b','FIREBurn'),
 (r'\bwhistle.{0,4}police\b','WHSTMech'),
 (r'^fog horn$','HORNAir'),
 (r'\bdoor.{0,6}wooden\b','DOORWood'),
 (r'\bdoor.{0,6}metal\b','DOORMetl'),
 (r'\bdoor.{0,6}medicine cabinet\b','DOORCab'),
 (r'\bdoor.{0,6}refrigerator\b','DOORAppl'),
 (r'\bdoor latch\b','DOORHdwr'),
 (r'\bgarage door.{0,4}electric|\bdoor.{0,4}automatic sensor\b','DOORElec'),
 (r'\blight switch\b','MECHSwtch'), (r'^lock (?:open|close)\b','MECHLock'),
 (r'\bzipper\b','OBJZipr'), (r'\bsuitcase\b','OBJLug'),
 (r'\bpage turns\b','PAPRHndl'), (r'\bpaper.{0,4}tearing\b','PAPRRip'),
 (r'\bpaper.{0,4}crumbling\b','PAPRHndl'),
 (r'\bstapler\b','OBJOffc'), (r'\bcoins?\b','OBJCoin'),
 (r'\bporch swing\b','OBJFurn'),
 (r'\bblinds\b|\bwindow shade\b','WNDWCover'),
 (r'\bcamera\b','COMCam'), (r'\bprojector\b','COMAv'),
 (r'\b(?:cash register|supermarket checkout)\b','MACHOffc'),
 (r'\b(?:copier|printer|caculator|pencil sharpener)\b','MACHOffc'),
 (r'\bair conditioner|\bfurnace\b','MACHHvac'),
 (r'^fan\b','MACHFan'), (r'\belevator\b','MACHElev'),
 (r'\b(?:lathe|milling machine|conveyor belt|drill press|boiler room|power plant|generator)\b','MACHInd'),
 (r'\b(?:table saw|table sander|grinder|drill.{0,4}electric|drill.{0,4}high impact|steel cutter)\b','TOOLPowr'),
 (r'\b(?:sawing wood|hammer on anvil)\b','TOOLHand'),
 (r'\b(?:lawn mower|hedge trimmer)\b','MACHGrdn'),
 (r'\b(?:vacuum|blender|washing machine|clothes dryer|hair dryer|shaver|microwave|perculator|humidifier|waxing and polishing machine)\b','MACHAppl'),
 (r'\bsump pump\b','MACHPump'),
 (r'\b(?:broom|brushing teeth|shower curtain)\b','OBJHsehld'),
 (r'\btoboggan\b','SPRTWntr'),
 (r'\barc welding\b','ELECArc'),
 (r'\bdigging (?:dirt|in stony ground)\b','DIRTMvmt'),
 (r'\bdigging in wet muddy ground\b','LIQMvmt'),
 (r'\brocks?.*\b(?:throwing|moving)\b','ROCKMvmt'),
]

def match(pattern, text):
    return re.search(pattern, text, flags=re.I) is not None

def parappa_label(description):
    """Reviewed anime-effect filename phrases; visual cues alone stay broad.

    A blink, gesture or shock scene does not establish the audible instrument.
    Explicit comic acoustic terms do establish a cartoon leaf; literal devices
    are kept in their source categories rather than called cartoon machines.
    """
    d = description.lower()
    literal = [(r'film projector', 'COMAv'), (r'telephone ring', 'COMTelph')]
    for pattern, catid in literal:
        if match(pattern, d):
            return catid, None, 'sfx', 'Explicit literal device in anime-effect filename: ' + pattern
    if match(r'\bdoor open\b', d):
        return None, 'DOORS', 'sfx', 'Door opening named; door material/mechanism unspecified.'
    if match(r'\b(?:footsteps?|footstep)\b', d):
        return None, 'FOOTSTEPS', 'sfx', 'Stylized footsteps named; human/animal/creature actor not established by the filename.'
    # Combined named effects retain component proposals without choosing one.
    if match(r'whistle.*(?:ker[ -]?splat|splatt)|creak-stretch-squeak|head bonk bell gong boing', d):
        return None, 'CARTOON', 'sfx', 'Several named comic components; proposed leaves retained, no single dominant component asserted.'
    acoustic = [
        (r'\banvil\b|metallic.*(?:hit|smack|bonk)|metallic head', 'TOONClang'),
        (r'\b(?:bonk|boink|smack|klonk|thud|impact)\b', 'TOONImpt'),
        (r'\bboing\b|tromboing|jew harp.*bounce', 'TOONBoing'),
        (r'\btwang\b', 'TOONTwang'),
        (r'\bwhistle\b', 'TOONWhis'),
        (r'\bsqueak\b', 'TOONSqk'),
        (r'\bstretch\b', 'TOONStrch'),
        (r'\b(?:ker[ -]?splatt?|splat)\b', 'TOONSplt'),
        (r'\b(?:zip|zing out)\b', 'TOONZip'),
        (r'\b(?:swish|swoosh|whoosh)\b', 'TOONSwsh'),
        (r'guitar pick', 'TOONPluk'),
        (r'\b(?:piano|xylo|cymbal|drum|cowbell|guitar|claves|woodblock|jew harp)\b|processed bell|bell pitch-bended', 'TOONMx'),
        (r'\b(?:snore|sigh|gulp|sniff|raspberry|razz|huh-afraid|huh-afriad)\b', 'TOONVox'),
        (r'funny birds chirp', 'TOONAnml'),
        (r'\bpop\b', 'TOONPop'),
    ]
    for pattern, catid in acoustic:
        if match(pattern, d):
            return catid, None, 'sfx', 'Explicit comic acoustic description in anime-effect library: ' + pattern
    return None, 'CARTOON', 'sfx', 'Anime/comic effect context; title gives a visual action or opaque cue without a supported acoustic subtype.'

def classify_description(description, context, library):
    """Return catid, broad category, content and inspectable evidence."""
    d = description.lower().replace('_', ' ')
    c = context.lower()
    # Mixed or contradictory descriptions must not become narrow training labels.
    if 'bird - canadian geese - flock.helicopter' in d:
        return None, 'AMBIENCE', 'ambience', 'Two clear sources (Canadian geese and idling helicopter); broad mixed-source ambience proposed, concurrence/segmentation pending, no dominant source asserted.'
    if 'fire, rumble, earthquake' in d:
        return None, 'NATURAL DISASTER', 'sfx', 'Composite disaster-effect description names fire, rumble and earthquake; subtype remains unset, component proposals retained, segmentation pending.'
    if d == 'fizz sound':
        return 'WATRFizz', None, 'sfx', 'Explicit fizz title; UCS WATER/FIZZ includes air fizzing in liquid and carbonated beverages. Source interpretation remains provisional.'
    if 'horses or cattle' in d:
        return 'FEETAnml', None, 'sfx', 'Title explicitly leaves animal species uncertain.'
    if match(r'\btelephone\b.*operator announces',d):
        return 'VOXFutz',None,'speech','Telephone operator announcement, not telephone mechanism or ringing.'
    if d == 'sonar pings':
        return 'BOATSub',None,'sfx','Explicit sonar pings; UCS BOATS-SUBMARINE definition includes sonar.'
    if d == 'horn - submarine dive':
        return 'ALRMSirn',None,'sfx','Explicit submarine dive alarm; UCS BOATS-SUBMARINE redirects it to ALARMS-SIREN.'
    if d in {'commodity exchange','stock exchange'}:
        return None,'AMBIENCE','ambience','Trading venue named; activity and narrower scene subtype unspecified.'
    if d == 'cement being poured from hopper':
        return None,'MACHINES','sfx','Hopper discharge explicitly described; machine subtype unspecified.'
    if match(r'^cement (?:vibrator|mixer)', d):
        return 'MACHCnst',None,'sfx','Explicit portable cement construction machine.'
    if 'man and woman' in d and match(r'laughing|giggling',d):
        return 'CRWDLaff',None,'sfx','Multiple people laughing; single-person VOICES-LAUGH leaf does not apply.'
    if 'man and woman' in d and match(r'crying|sobbing|screaming|moaning',d):
        return None,'CROWDS','sfx','Multiple voices explicitly named; narrower crowd subtype unspecified.'
    if 'no speech' not in d and match(r'operator announces|announcement|saying|talking|reciting|asking questions',d):
        content = 'speech'
    else:
        content = 'sfx'
    if d.startswith('coot.'):
        return 'BIRDWade',None,content,'Coot is the named subject; geese and mallard are background.'
    if match(r'^water.{0,4}brook',d):
        return 'WATRFlow',None,content,'Brook is the named subject; insect calls are background.'
    if 'audience presence' in d:
        return None,'CROWDS','ambience','Audience presence; quietness is not established by the title.'
    if 'general quarters announcement' in d:
        return None,'VOICES','speech','Announcement with alarm; retain as mixed speech, needs listening.'
    if 'children at balloon launch' in d:
        return 'CRWDChld',None,'speech','Children and spoken countdown described.'
    # Scene descriptions have priority over individual sources inside the scene.
    scenes = [
      (r'^hen house atmosphere$', 'AMBFarm'),
      (r'office (?:background|b.kgr)', 'AMBOffc'),
      (r'\b(?:airport|airfield|raf station)\b.*(?:atmos|ambience|activity)|(?:atmos|ambience).*\braf station\b|airport terminal|airport control tower|(?:interior of|ambience).*train station|(?:subway|central) station.*ambience','AMBTran'),
      (r'\b(?:forest|jungle)\b.*(?:ambience|atmosphere|background)|asian jungle|south american jungle','AMBForst'),
      (r'\bswamp\b.*ambience','AMBSwmp'),
      (r'\b(?:harbour|harbor)\b.*ambience','AMBNaut'),
      (r'\b(?:restaurant|diner)\b.*(?:ambience|background music)|army catering.*atmosphere','AMBRest'),
      (r'\b(?:foodstore|department store|shopping mall)\b.*ambience|courtroom atmosphere|museum.*atmosphere|auditorium.lobby','AMBPubl'),
      (r'\b(?:city|sidewalk)\b.*ambience','AMBUrbn'),
      (r'\bplayground\b','AMBSchl'),
      (r'^traffic\b','AMBTraf'),
      (r'\b(?:construction|construc.) (?:site|sequence)\b','AMBCnst'),
      (r'\bbattle\b.*ambience|parade ground atmosphere','AMBWar'),
      (r'ammunition factory.*(?:atmosphere|background)','AMBInd'),
      (r'^autumn.*atmosphere','AMBBird'),
      (r'crickets and peepers at pond','AMBInsc'),
      (r'^african bush after sunset','AMBMisc'),
      (r'\bscuba diver.*underwater ambience','AMBUndwtr'),
      (r'\bpool.{0,4}public|\brace track.{0,4}w announcer','AMBSprt'),
    ]
    for pattern, catid in scenes:
        if match(pattern,d):
            return catid,None,'ambience','Explicit scene description: '+pattern
    if 'ammunition factory' in d:
        return 'MACHInd',None,'sfx','Factory process described; not gunfire.'
    if 'schoolchildren' in d and 'singing' in d:
        return 'CRWDSing',None,'music','Children singing named songs.'
    if 'athletics meeting' in d:
        return 'AMBSprt',None,'ambience','Sports crowd mixed with stadium atmosphere explicitly described.'
    if match(r'^drill with orders',d):
        return None,'MOVEMENT','speech','Military drill with spoken orders; mixed actions need review.'
    if match(r'army drill|soldiers.*(?:marching|shambling)|soldier walking',d):
        return 'FEETHmn',None,'sfx','Human marching/walking explicitly described.'
    if 'soldiers moving through undergrowth' in d:
        return 'MOVEHmn',None,'sfx','Human movement through vegetation described.'
    if 'soldiers hammering' in d:
        return 'TOOLHand',None,'sfx','Hammering described.'
    if 'anne boleyn' in c and d == 'mechanism':
        return 'CLOCKMech',None,'sfx','Clock context with mechanism title.'
    # Vehicles: filename source outranks broad multi-topic disc headings.
    aircraft = match(r'\b(?:aircraft|airplane|helicopters?|airliner|concorde)\b',d) or (library=='BBC' and c.startswith('aircraft'))
    if aircraft:
        if match(r'\bdoor\b',d): leaf='AERODoor'
        elif match(r'\bhelicopter',d): leaf='AEROHeli'
        elif match(r'\b(?:interior|cabin|flightdeck|cockpit|c.pit)\b',d): leaf='AEROInt'
        elif match(r'\b(?:fighter|bomber|lightnings?|wwii|world war ii)\b',d): leaf='AEROMil'
        elif match(r'\b(?:piston|prop|turboprop|prop-jet|auster)\b',d): leaf='AEROProp'
        elif match(r'\bjet\b|concorde|\b707\b|\btrident\b',d): leaf='AEROJet'
        elif match(r'\bgliders?\b',d): leaf='AEROMisc'
        elif match(r'\b(?:douglas dc3|viscount)\b',d): leaf='AEROProp'
        else: leaf=None
        return leaf,None if leaf else 'AIRCRAFT',content,'Aircraft source and explicit component/type; broad when unspecified.'
    train = match(r'^train\b|^cable car\b',d)
    if train:
        if 'subway' in d: leaf='TRNSbwy'
        elif 'steam' in d: leaf='TRNSteam'
        elif 'cable car' in d: leaf='TRNTram'
        else: leaf=None
        return leaf,None if leaf else 'TRAINS',content,'Train type explicitly named; no type inferred when absent.'
    boat = match(r'\b(?:boat|tugboat|ferry)\b',d) or 'speedboat' in c
    if boat:
        if 'waves against' in d: leaf='BOATWash'
        elif 'fog horn' in d: return 'HORNAir',None,content,'Fog horn explicitly named; UCS BOATS-HORN redirects fog horns to HORNS-AIR POWERED.'
        elif 'horn' in d: leaf='BOATHorn'
        elif 'interior' in d and 'exterior or interior' not in d: leaf='BOATInt'
        elif match(r'\bmotor boat|\boutboard|\binboard',d) or 'speedboat' in c: leaf='BOATMotr'
        elif 'ferry' in d or 'tugboat' in d: leaf='BOATShip'
        else: leaf=None
        return leaf,None if leaf else 'BOATS',content,'Boat source/component explicitly described.'
    road = match(r'\b(?:automobile|car|truck|firetruck|motorcycle|bulldozer|tractor|cross-country vehicle)\b',d) or (library=='BBC' and match(r'\b(?:van|truck|austin maestro|austin gipsy)\b',c))
    if road:
        if 'radio, police' in d: return 'COMTran',None,content,'Police radio is subject, vehicle is context.'
        if match(r'warning (?:buzzer|bell)|voice warning|seat belt warning',d): leaf='VEHAlrm'
        elif match(r'\bhorn\b',d): leaf='VEHHorn'
        elif match(r'\b(?:door|doors|hood|bonnet|boot|trunk(?! road))\b',d): leaf='VEHDoor'
        elif match(r'\bwindow\b|sun roof',d): leaf='VEHWndw'
        elif match(r'\bbrakes?\b',d): leaf='VEHBrake'
        elif match(r'\b(?:wipers|indicators|seat belt|gas cap|heater boost|blower)\b',d): leaf='VEHMech'
        elif 'skid' in d: leaf='VEHSkid'
        elif 'motorcycle' in d: leaf='VEHMoto'
        elif 'firetruck' in d: leaf='VEHEmrg'
        elif match(r'\b(?:bulldozer|cement mixer truck)\b',d): leaf='VEHCnst'
        elif 'tractor' in d: return None,'VEHICLES',content,'Tractor use (farm/construction) not established by title.'
        elif 'truck' in d or match(r'\bvan\b',c): leaf='VEHTruck'
        elif 'gipsy' in c: return None,'VEHICLES',content,'Cross-country vehicle named; UCS road subtype unspecified.'
        else: leaf='VEHCar'
        return leaf,None,content,'Road vehicle type/component explicitly described.'
    if 'tank - army' in d: return 'VEHMil',None,content,'Army tank named.'
    if 'rocket' in d: return 'AERORckt',None,content,'Rocket flight/launch named.'
    for pattern,catid in RULES:
        if match(pattern,d):
            if catid=='MUSCPrfm':content='music'
            return catid,None,content,'Explicit filename phrase: '+pattern
    broad = [(r'\bexplosion\b','EXPLOSIONS'), (r'\bbell\b','BELLS'),
             (r'\bdoor\b','DOORS'), (r'\bdrawer\b','DRAWERS'),
             (r'^window\b','WINDOWS'), (r'\bclock\b','CLOCKS'),
             (r'^water\b','WATER'), (r'^birds?\b','BIRDS'),
             (r'^horn\b|^fog horn\b','HORNS'),
             (r'\bcompressor\b|\bcement (?:mixer|vibrator)\b','MACHINES'),
             (r'\bcrane\b','VEHICLES'), (r'^group.{0,4}small','MOVEMENT'),
             (r'\belectric sign\b|\bturnstile\b|\bpump.{0,4}tire\b','MECHANICAL'),
             (r'^laughter','VOICES'), (r'\bvelcro\b','CLOTH'),
             (r'\b(?:soda can|tea pot)\b','FOOD & DRINK'),
             (r'^refrigerator.{0,4}move','OBJECTS')]
    for pattern,category in broad:
        if match(pattern,d):return None,category,content,'Source known; leaf unspecified: '+pattern
    return None,None,'unknown','No sufficiently specific supported metadata rule; needs review.'

def rows(root, ucs):
    for library in LIBRARIES:
        folder = root/library
        if not folder.exists(): continue
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in AUDIO: continue
            rel=path.relative_to(root).as_posix()
            context=path.parent.relative_to(folder).as_posix()
            description=path.stem
            game_function=None
            if library=='BBC':
                description=re.sub(r'\.\d{8}$','',description).rstrip('.')
            if library=='valentinosoundeffectslibrary':
                description=re.sub(r'^\d+\.\s*','',description)
            if library in {'HB01 - Hanna-Barbera Sound FX Library', 'Hanna-Barbera Sound FX Library'}:
                family=re.sub(r' HB\d+.*$','',description)
                description=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',family)
                catid=HB.get(family)
                category=HB_BROAD.get(family)
                if not catid and ('Cartoon' in family or family=='Cartoon' or family=='RollerSkateCartoo'):
                    category='CARTOON'
                content='ambience' if family.startswith('Battle') else 'sfx'
                reason='Exact observed Hanna-Barbera filename family: '+family
                if not catid: reason+='; action/source insufficient for a narrower leaf.'
                context=family
            elif library == 'PaRappa TV Anime-Animation Sound FX':
                catid,category,content,reason=parappa_label(description)
            elif library=='rpgmaker2k':
                family=re.sub(r'\d+$','',description)
                catid,category=RPG.get(family,(None,None))
                game_function=family
                content='sfx' if catid or category else 'unknown'
                reason='RPG Maker filename: '+family+'; provisional source interpretation.' if catid or category else 'Gameplay action/status name only; audible source is not established.'
                if family in RPG_EVENTS:
                    reason='Explicit RPG game event/status cue: '+family+'; videogame function established, no physical source or acoustic subtype asserted.'
                elif family in RPG_MAGIC:
                    reason=('RPG-effect theme Earth interpreted as elemental magic, consistent with the numbered elemental-cue families; intended theme proposed, not a claim of recorded earth or an audio-verified realization.' if family=='Earth' else 'RPG-effect theme '+family+' interpreted as magic; supplied UCS explicitly includes holy/dark/ice magic. Intended theme proposed, acoustic realization unverified.')
                context=family
            else:
                catid,category,content,reason=classify_description(description,context,library)
            if catid:category=ucs[catid]['category']
            row={'path':rel,'description':description,'original_category':context,
                 'catid':catid,'category':category,
                 'confidence':'medium' if catid else ('low' if category else 'none'),
                 'reason':reason,'content':content,
                 'metadata_source':'filename+parent_directory',
                 'label_status':'provisional','audio_verified':False}
            if game_function:row['game_function']=game_function
            if game_function in RPG_EVENTS or game_function in RPG_MAGIC:
                row['confidence']='low'
            if library == 'rpgmaker2k' and not row['category']:
                # Verified RTP family membership organizes assets without inventing
                # a physical source from an abstract effect name.
                source_url = 'https://github.com/EasyRPG/Player/blob/master/src/rtp_table.cpp'
                source_aliases = {'Breast':'breath', 'Chaos':'confusion',
                                  'Sonic1':'sound wave 1', 'Sonic2':'sound wave 2',
                                  'Wall1':'magic 1', 'Wall2':'magic 2'}
                if description in {'Wall1', 'Wall2'}:
                    row.update(category='MAGIC', confidence='low', content='sfx',
                               game_role_known=True, acoustic_event_category_known=False,
                               classification_scope='declared_game_role',
                               classification_confidence_scope='intended_game_role',
                               confidence_scope='intended_role_only', training_eligible=False,
                               reason='EasyRPG primary RTP alias table maps legacy '+description+' to magic; intended magic cue category established. Audible realization and physical source unresolved; no human audio verification.')
                else:
                    row.update(category='GAMES', confidence='low', content='unknown',
                               classification_scope='source_context',
                               classification_confidence_scope='source_context',
                               confidence_scope='source_context_only', semantic_role_known=False,
                               game_role_known=False, training_eligible=False,
                               reason='Source-context grouping only: confirmed RPG Maker 2000 RTP game-audio family. Specific audible source/event and intended function remain unresolved; no console-specific category or semantic sound-event label inferred. Not eligible for semantic audio-model training.')
                row.update(source_context='RPG Maker 2000 RTP game audio', source_context_evidence_urls=[source_url])
                if description in source_aliases:
                    row['verified_rtp_alias'] = source_aliases[description]
                row['source_context_evidence'] = 'EasyRPG primary RTP alias table records the legacy sound filename family; aliases establish names, not physical source or human listening verification.'
            if library == 'PaRappa TV Anime-Animation Sound FX' and 'Several named comic components' in reason:
                row['proposed_catids']=[catid for token,catid in [('whistle','TOONWhis'),('splat','TOONSplt'),('creak','TOONCreak'),('stretch','TOONStrch'),('squeak','TOONSqk'),('clang','TOONClang'),('pop','TOONPop'),('bonk','TOONImpt'),('gong','TOONMx'),('boing','TOONBoing')] if token in description.lower()]
                row['segmentation_status']='pending'
            if library == 'valentinosoundeffectslibrary':
                if description == 'Bird - Canadian Geese - Flock.Helicopter - Idling':
                    row['proposed_catids']=['BIRDFowl','AEROHeli']
                    row['named_sources']=['Canadian geese flock','idling helicopter']
                    row['segmentation_status']='pending'
                elif description == 'Fire, Rumble, Earthquake':
                    row['proposed_catids']=['NATDQuak']
                    row['proposed_categories']=['FIRE','NATURAL DISASTER']
                    row['named_sources']=['fire','rumble','earthquake']
                    row['segmentation_status']='pending'
            yield row

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--ucs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    data=json.loads(args.ucs.read_text(encoding='utf-8-sig'))
    ucs={item['catid']:item for item in data}
    categories={item['category'] for item in data}
    result=list(rows(args.root,ucs))
    assert len({row['path'] for row in result})==len(result)
    for row in result:
        assert (args.root/row['path']).is_file(),row['path']
        assert row['catid'] is None or row['catid'] in ucs,row
        assert row['category'] is None or row['category'] in categories,row
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in result),encoding='utf-8')
    counts=collections.Counter((row['path'].split('/')[0], 'leaf' if row['catid'] else 'broad' if row['category'] else 'unresolved') for row in result)
    print(json.dumps({'files':len(result),'counts':{' / '.join(k):v for k,v in sorted(counts.items())}},indent=2))

if __name__=='__main__':main()
