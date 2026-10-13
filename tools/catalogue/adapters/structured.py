"""Recover Wayzata and Universal catalogue descriptions without changing originals.

All labels are provisional metadata interpretations, never listening verification.
Universal index durations are descriptive lengths, NOT offsets into the MP3.
Uses deliberately scoped mappings, not UCS synonym substring voting.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

WAYZATA = "Sound Library Pro - Wayzata Technology (1993)"
UNIVERSAL = "universal-studios-sound-effects-library"

FOLDER_NAMES = {"ANIMALS": "Animals", "HOUSE": "Household", "HOUSEHOL": "Household",
    "INST": "Instruments", "INSTRUME": "Instruments", "NATURE": "Nature", "SPEC": "Spec Eff",
    "SPEC_EFF": "Spec Eff", "VOICE": "Voice", "BOUNCE": "Bounce/Spring", "BOUNCE_S": "Bounce/Spring",
    "ELEC": "Electronic", "ELECTRON": "Electronic", "PERC": "Percussion", "PERCUSSI": "Percussion",
    "SIRENS": "Sirens/alarms/bells", "SIRENS_A": "Sirens/alarms/bells", "TRANS": "Transportation",
    "TRANSPOR": "Transportation", "ALPHA": "Alphabet", "ALPHABET": "Alphabet",
    "MAC": "Macintosh Phrases", "MACINTOS": "Macintosh Phrases"}

def canonical_key(parts):
    """Explicit publisher folder aliases; punctuation-only stem normalization."""
    return tuple(FOLDER_NAMES.get(x.upper(), x.title()).lower() for x in parts[:-1]) + (re.sub(r"[^a-z0-9]", "", Path(parts[-1]).stem.lower()),)

# Publisher headings reviewed against UCS 8.2.1. Broad/ambiguous headings
# deliberately retain only a parent category (prefixed with @).
UNIVERSAL_MAP = {
    "AIRPORT, AMBIENCE": "AMBTran", "AIRPLANE, CRASH": "@DESTRUCTION",
    "DIRIGIBLE": "AEROMisc", "HELICOPTER": "AEROHeli",
    "AMUSEMENT PARK, GAME": "GAMEMisc", "ALLIGATOR": "ANMLRept",
    "BATS": "ANMLBat", "BEAR": "ANMLWild", "BEES": "ANMLInsc",
    "BULL": "ANMLFarm", "COUGAR": "ANMLWcat", "DOLPHIN": "ANMLAqua",
    "ELEPHANT": "ANMLWild", "FROG": "ANMLAmph", "GOAT": "ANMLFarm",
    "GUINEA PIG": "ANMLRdnt", "LEOPARD": "ANMLWcat", "LION": "ANMLWcat",
    "MONKEY": "ANMLPrim", "MONSTER": "CREAMnstr", "ROOSTER": "BIRDFowl",
    "SEAL": "ANMLAqua", "SHEEP": "ANMLFarm", "SQUIRREL": "ANMLRdnt",
    "TIGER": "ANMLWcat", "WOLF": "ANMLWdog", "ARCHERY": "@WEAPONS",
    "AVALANCHE": "NATDAval", "BATTERING RAM": "WEAPSiege",
    "BODYFALL, HUMAN": "FGHTBf", "BOXING": "FGHTImpt",
    "BUBBLE, SULPHUR": "@GEOTHERMAL", "BUCKET, METAL": "@METAL",
    "CATAPULT": "WEAPSiege", "CLICK": "@MECHANICAL", "CLIMB, ICE": "@ICE",
    "COIN, TAP": "OBJCoin", "COMEDY": "@CARTOON",
    "CRASH, BUILDING": "DESTRClpse", "CRASH, CART": "DESTRCrsh",
    "CRASH, CHINA": "CERMCrsh", "CRASH, CLOSET": "DESTRCrsh",
    "CRASH, CUPBOARD": "DESTRCrsh", "CRASH, DISHES": "FOODTware",
    "CRASH, GARBAGE": "DESTRCrsh", "CRASH, MISCELLANEOUS": "DESTRCrsh",
    "CRASH, PIGGY BANK": "DESTRCrsh", "CRASH, TABLE": "DESTRCrsh",
    "CRASH, TREE": "WOODCrsh", "CROWD, CHEERING": "CRWDCheer",
    "DISHES, GLASS, TOAST": "FOODGware", "DOOR, PRISON": "DOORPrisn",
    "DOOR, WOOD": "DOORWood", "EARTHQUAKE": "NATDQuak",
    "ELECTRICITY": "@ELECTRICITY", "EXPLOSION, JET": "@EXPLOSIONS",
    "EXPLOSION, UNDERWATER": "@EXPLOSIONS", "FIRE, AMBIENCE": "FIREBurn",
    "FIRE, FLASH": "FIREBrst", "GLASS, HIT": "GLASImpt",
    "GLASS, KICK": "GLASImpt", "GRIND, GEARS": "MECHGear",
    "GUILLOTINE": "WEAPMisc", "HIT, HUMAN": "FGHTImpt", "HOOK, BOAT": "@TOOLS",
    "HORN, ALERT": "@HORNS", "HORN, ANTIQUE": "@HORNS", "HORN, BOAT": "BOATHorn",
    "HORN, BULB": "HORNAir", "HORN, FOG": "BOATHorn", "HORN, KLAXON": "@HORNS",
    "HORN, RAM": "HORNTrad", "HORN, SHIP": "BOATHorn", "HORN, TRAIN": "TRNHorn",
    "KICK, HUMAN": "FGHTImpt", "KICK, TIRE": "RUBRImpt", "KNIFE, THROW": "WEAPKnif",
    "METAL, BANG": "METLImpt", "METAL, HAMMER": "METLImpt", "METAL, HIT": "METLImpt",
    "PUNCH, FACE": "FGHTImpt", "PURSE, DUMP": "OBJBag", "RADIO, TUNING": "COMRadio",
    "ROCK": "@ROCKS", "SHARK, 'JAWS'": "CREAAqua", "SIREN, AIR RAID": "ALRMSirn",
    "SIREN": "ALRMSirn", "SLAP, FACE": "FGHTImpt", "SPACE, COMPUTER": "SCICmpt",
    "SPACE, CONTROL ROOM": "AMBSci", "SPACE, DOOR": "SCIDoor",
    "SPACE, GUN SHOTS": "SCIWeap", "SPACE, ROBOT": "@ROBOTS", "SPACE, SHIP": "SCIShip",
    "SPACE": "@SCIFI", "SPACE, VEHICLE": "SCIVeh", "SPEAR": "WEAPPole",
    "SQUEAK, BRAKES": "VEHBrake", "SWORD": "WEAPSwrd", "SWORD, FIGHT": "WEAPSwrd",
    "TELEGRAPH, RECEIVE": "COMTelm", "TELEGRAPH, SEND": "COMTelm",
    "TRAIN, STEAM": "TRNSteam", "UNDERWATER": "WATRUndwtr", "VOLCANO": "NATDVolc",
    "WATER, POUR": "WATRPour", "WATER, SPLASH": "WATRSplsh", "WEREWOLF": "CREABeast",
    "WHIP": "WEAPWhip", "WHISTLE, FACTORY": "WHSTMech", "WHISTLE, HUMAN": "WHSTHmn",
    "WHISTLE, POLICE": "WHSTMech", "WHISTLE, SHIP": "BOATHorn",
    "WHISTLE, TRAIN": "TRNHorn", "WHISTLE, TUBE": "WHSTMech",
    "WOOD, HAMMER": "WOODImpt", "WOOD, PRY": "@WOOD", "WOOD, ROLL": "WOODMvmt",
    "GRENADE, HAND": "@EXPLOSIONS", "BAZOOKA": "GUNArtl", "CANNON, MILITARY": "GUNCano",
    "ROCKET": "@WEAPONS", "BOMB, WHISTLE": "WEAPMisc", "EXPLOSION": "@EXPLOSIONS",
    "DEPTH CHARGE": "@EXPLOSIONS", "TORPEDO": "WEAPMisc", "SONAR": "COMTelm",
    "SUBMARINE": "BOATSub", "TANK, MILITARY": "VEHMil", "FENCING": "WEAPSwrd",
    "MARCHING": "FEETHmn", "CROWD, CHANT": "@CROWDS", "GUN, HAND, FOLEY": "GUNMech",
    "GUN, SILENCER": "GUNSupr", "GUN, HAND GUN": "GUNPis", "GUN, RIFLE, FOLEY": "GUNMech",
    "GUN, MUSKET": "GUNAntq", "GUN, RIFLE": "GUNRif", "GUN, SHOT GUN": "GUNShotg",
    "GUN, BULLET WHINE": "BLLTBy", "GUN, RICOCHET": "BLLTRico",
    "GUN, MACHINE GUN": "GUNAuto", "GUN, MACHINE, FOLEY": "GUNMech",
    "BATTLE, MILITARY": "AMBWar", "INDIANS": "@VOICES", "AMBIENCE, STREET": "AMBHist",
    "FIGHT, SALOON": "@FIGHT", "FIGHT, SWORD": "WEAPSwrd", "FIGHT, WESTERN": "@FIGHT",
    "BATTLE, WESTERN": "AMBWar", "DOOR, JAIL": "DOORPrisn", "STAMPEDE, CATTLE": "FEETAnml",
    "WAGON": "VEHWagn", "WAGON TRAIN": "VEHWagn", "WAGON, CRASH": "DESTRCrsh",
    "STAGECOACH": "VEHWagn", "HORSE, WALK": "FEETHors", "HORSE, TROT": "FEETHors",
    "HORSE, CANTER": "FEETHors", "HORSE, GALLOP": "FEETHors", "CAVALRY, HORSES": "FEETHors",
}

# Whole tokens/phrases, evaluated only within the relevant publisher families.
ANIMALS = [
    (r"seagull\d*|seagulls", "BIRDSea"), (r"herons|cranes", "BIRDWade"),
    (r"owl|vulture", "BIRDPrey"), (r"crow|caw", "BIRDCrow"),
    (r"duck|madduck|mallard|scrdduck|geese|cangeese|turkey|chicken|chicks|babychk2|babychks|cluck|rooster|rostr", "BIRDFowl"),
    (r"parrot|parakeet|macaw", "BIRDTrop"),
    (r"cuckoo|woodpckr", "BIRDMisc"),
    (r"canaries|cardinal|dove|doves|mckngbrd|medwlrk|pigeons|robin|sparrows|finch", "BIRDSong"),
    (r"whale|whales|seal|sea lion", "ANMLAqua"),
    (r"cougar|lion|lioness|leopard|lynx|puma|tiger\d*|lions", "ANMLWcat"),
    (r"cat|kitten|kittens|meow", "ANMLCat"),
    (r"wolf|wolves|coyote|foxes|wild dogs", "ANMLWdog"),
    (r"dog|dogs|puppy|puppies|bark|hound|hounds|bloodhound|bloodhou|bldhound|kennel|bernard", "ANMLDog"),
    (r"horse\d*|horses|donkey|trot|trot2|trot3", "ANMLHors"),
    # Species precedes the generic sex term 'bull' (e.g. bull elephant).
    (r"bear|grizzly|elephant|elephants|rhinoceros|caribou|camel", "ANMLWild"),
    (r"cow|cows|cattle|calves|bull|goat|goats|sheep|lamb|pig|piglet|hogs\d*|baaaa|mooo", "ANMLFarm"),
    (r"chimp|chimpanzees|gorilla|monkey|monkeys|orangutan", "ANMLPrim"),
    (r"bee|bees|beehive|cricket\d*|crickets|mosquito|mosq|wasp", "ANMLInsc"),
    (r"frog|bullfrog|toad", "ANMLAmph"), (r"cobra", "ANMLRept"),
]
HOUSE = [
    (r"close shower curtain", "OBJHsehld"), (r"drop the bucket", "OBJCont"),
    (r"noisemaker|lo noisemaker", "@TOYS"),
    (r"baby|babytalk", "VOXBaby"), (r"bicycle bell", "BELLMisc"),
    (r"air conditioner|furnace", "MACHHvac"),
    (r"blender|dustbuster|electric shaver|hair dryer|washing machine", "MACHAppl"),
    (r"blinds", "WNDWCover"), (r"broken dish", "CERMBrk"), (r"door creaking", "DOORCreak"),
    (r"doorbell", "BELLDoor"), (r"doorknob", "DOORHdwr"), (r"sliding closet door", "DOORSlid"),
    (r"door", "@DOORS"), (r"drawer", "@DRAWERS"), (r"lock", "MECHLock"),
    (r"phone|telephone", "COMTelph"), (r"typewriter|type tic", "COMType"),
    (r"camera", "COMCam"), (r"cash register", "MACHOffc"),
    (r"down the drain|draining bath|water down drain", "WATRDran"),
    (r"toilet|shower on", "WATRPlmb"), (r"drip", "WATRDrip"),
    (r"aerosol|pressurized", "@AIR"), (r"sump pump", "MACHPump"),
    (r"buckling seatbelt", "VEHMech"), (r"tea pot", "FOODKware"),
    (r"pop can open|soda can tab", "OBJCont"),
    (r"brooming|sweep|mailbox", "OBJHsehld"),
    (r"fireplace", "FIREBurn"), (r"paper torn|scissors on paper", "PAPRRip"),
    (r"crumpled paper", "PAPRHndl"), (r"book dropped", "OBJBook"),
    (r"sneezing", "HMNSneez"), (r"cough|clearing throat", "HMNCough"),
    (r"snore|snoring", "HMNSnor"), (r"sniffle", "HMNSniff"),
    (r"clap|claps", "HMNSkin"), (r"chomp\d*|potato chip", "FOODEat"),
    (r"drink", "FOODDrnk"), (r"pouring soda", "FOODPour"),
    (r"bubbling stew|sizzling", "FOODCook"), (r"egg break", "FOODIngr"),
    (r"glass on saucer|ice in glass|mason jar", "FOODGware"), (r"glass", "@GLASS"),
    (r"ice cracking", "ICEBrk"), (r"pencil|pen", "OBJWrite"),
    (r"alarm clock", "CLOCKMech"), (r"passing breeze", "WIND"),
    (r"squeaky bed", "OBJFurn"), (r"hand stapler", "OBJOffc"),
    (r"dice", "GAMEBoard"), (r"digging dirt", "DIRTMvmt"),
]
NATURE = [(r"wind and thunder|storm|rainstorm|hurricane|sandstorm", "STORM"),
    (r"thunder|thundercrash|lightning", "THUN"), (r"wind|winds|windy|breeze|blowing", "WIND"),
    (r"rain", "RAIN"), (r"waterfall|niagara", "WATRFall"),
    (r"brook|stream|running water|rushing water", "WATRFlow"),
    (r"splash", "WATRSplsh"), (r"wave|waves", "WATRWave"), (r"swamp", "AMBSwmp")]
PEOPLE = [(r"applause", "CRWDApls"), (r"canned laughter", "CRWDLaff"),
    (r"laughter|giggle|haha|hahaha", "VOXLaff"), (r"scream", "VOXScrm"),
    (r"conversations", "CRWDConv"), (r"crowd", "@CROWDS"),
    (r"footsteps|steps|walk|running on gravel", "FEETHmn"),
    (r"heartbeat", "HMNHart"), (r"kiss|pucker up", "HMNKiss"),
    (r"cough", "HMNCough"), (r"oxygen mask", "@HUMAN"), (r"choir", "MUSCChor"),
    (r"holler", "VOXScrm"), (r"nyah-nyah", "@VOICES"), (r"yawn", "HMNBrth"),
    (r"ouch|ow|surprise", "VOXReac")]

def match_rules(text, rules):
    for pattern, catid in rules:
        if re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)", text, re.I):
            return catid, "medium", "Reviewed phrase mapping: " + pattern
    return None

def wayzata_label(description, original):
    d = description.lower()
    family, _, subgroup = original.partition(" / ")
    subgroup = subgroup.split(" / ")[0]
    if family == "Household" and d == "fizz":
        return "WATRFizz", "medium", "Publisher explicitly names fizz; UCS WATER/FIZZ includes air fizzing in liquid and carbonated beverages.", "sfx"
    if subgroup == "Military" and d in {"demolition crew", "demolition crew to"}:
        return "@DESTRUCTION", "medium", "Publisher names demolition; broad event category only, with no assumed explosion, collapse or material.", "sfx"
    if subgroup == "Misc" and d == "water and industry":
        return "@WATER", "medium", "Publisher explicitly names water with an industrial component. Mixed source; no dominant component or water action asserted.", "sfx"
    # Exact reviewed descriptions and surviving 8.3 stems. These mappings are
    # restricted to publisher sections, so words such as 'pop' or 'strike'
    # cannot assign a material or a cartoon style throughout the collection.
    reviewed = {
        "Animals": {
            "cat and kitten": "ANMLCat", "chimp&orangutan": "ANMLPrim",
            "herons and cranes": "BIRDWade", "sheep and goats": "ANMLFarm",
            "wild dogs and wolves": "ANMLWdog", "brar roar and scratch": "ANMLWild",
            "peacock": "BIRDFowl", "peacock2": "BIRDFowl", "lapwing": "BIRDWade",
            "loon": "BIRDMisc", "canada g": "BIRDFowl", "waterfou": "BIRDFowl",
            "meadowla": "BIRDSong", "mockingb": "BIRDSong", "woodpeck": "BIRDMisc",
            "pigeon f": "BIRDMisc", "scared d": "BIRDFowl",
            "baby2chi": "BIRDFowl", "babychic": "BIRDFowl", "roosterc": "BIRDFowl",
            "chickenc": "AMBFarm", "loud coo": "AMBFarm", "zoo": "@AMBIENCE"},
        "Instruments": {"sleigh bells": "MUSCBell", "bell tre": "MUSCChim",
            "cow bell": "BELLAnml", "bicycle": "BELLMisc",
            "(1) hi marimbula": "MUSCInst", "(1) lo marimbula": "MUSCInst",
            "(1) marimbula": "MUSCInst", "(full) marimbula": "MUSCInst"},
        "Military": {"all men on deck to": "@VOICES", "alarm to": "@ALARMS",
            "anti-aircraft fire to": "GUNArtl", "missile to": "AERORckt",
            "crash to": "@DESTRUCTION", "destruction to": "@DESTRUCTION",
            "electric shot to": "@SCIFI",
            "passing shot to": "BLLTBy"},
        "Misc": {"broken music": "@MUSICAL", "drum dance": "MUSCPerc",
            "orchestra": "MUSCSmpl", "orch long": "MUSCSmpl",
            "power chord": "@MUSICAL", "vibra-string": "@MUSICAL",
            "flanged metal": "DSGNDist", "ghost with stomach ache": "CREAEthr",
            "gremlin": "@CREATURES", "handcuffs": "EQUIPTact",
            "hubbub": "@CROWDS", "mechanical arm": "@MECHANICAL",
            "metal on metal": "@METAL", "metalwork": "@METAL",
            "popping water": "WATRBubl", "turnstile": "@MECHANICAL",
            "waterwheel": "@MACHINES", "wind tunnel": "AIRBlow",
            "smashing": "@DESTRUCTION", "trudging": "FEETHmn",
            "deflating": "AIRHiss", "humph?": "@VOICES",
            "twitch": "@MOVEMENT"},
        "People": {"swallow": "FOODEat", "falling!": "FGHTBf",
            "falling downward": "FGHTBf", "shiver": "MOVEHmn",
            "ow voice": "VOXReac"},
        "Sirens/alarms/bells": {"chime": "@BELLS", "chimed b": "@BELLS",
            "long chi": "@BELLS", "police w": "WHSTMech",
            "buoy": "@BELLS", "mechanical resonance": "@MECHANICAL",
            "screeching alarm": "@ALARMS", "wrong answer": "@USER INTERFACE"},
        "Transportation": {"beep-beep!": "VEHHorn", "cycle arrives": "VEHMoto"},
        "Household": {"jump on bed": "OBJFurn"},
    }
    lookup = reviewed.get(family if family in ("Animals", "Instruments", "Household") else subgroup, {})
    if d in lookup:
        target = lookup[d]
        abbreviated = description.isupper() or d in {"brar roar and scratch", "orch long"}
        return target, "low" if abbreviated or target.startswith("@") else "medium", "Reviewed exact publisher description/stem in " + original, "ambience" if target.startswith("AMB") else "speech" if d == "all men on deck to" else "sfx"
    if family == "Voice":
        special = match_rules(d, [(r"blow(?: hi| 2)?", "HMNBlow"), (r"chomp(?: hi)?", "FOODEat")])
        if special:
            return (*special, "sfx")
        # An explicit gender word outranks the F-/M- shorthand; F-male is
        # the spoken alphabet letter F, not a female prefix.
        gender = "VOXFem" if "female" in d else "VOXMale" if "male" in d else "VOXFem" if re.search(r"\(f\)|^f-", d) else "VOXMale" if re.search(r"\(m[123]?\)|^m-", d) else "@VOICES"
        content = "speech" if subgroup in ("Alphabet", "Numbers", "Macintosh Phrases") or gender != "@VOICES" else "unknown"
        return gender, "medium", "Publisher voice section; gender only when explicitly described", content
    if family == "Instruments":
        if subgroup == "Electronic":
            return "MUSCSynth", "medium", "Publisher Instruments / Electronic section", "sfx"
        # Horn/whistle samples in the instrument collection are not all brass/woodwind.
        rules = [(r"carhorn", "VEHHorn"), (r"shiphorn", "BOATHorn"), (r"foghorn", "HORNAir"),
                 (r"whistle|whistle2|whstle2", "WHSTMech"), (r"sax", "MUSCWind"),
                 (r"piano|pianokey|harpsichord|celesta|locelesta", "MUSCKeyd"),
                 (r"snapping fingers", "HMNSkin"), (r"gong", "MUSCBell"),
                 (r"marimba|lujon", "MUSCTnprc"), (r"marimbula", "@MUSICAL"),
                 (r"castanets|tambourine|rattler", "MUSCShake"), (r"triangle", "MUSCInst")]
        hit = match_rules(d, rules)
        if hit:
            return (*hit, "sfx")
        # Bells subfolder includes bicycle, hotel and ship bells; musical
        # use or tuning cannot be inferred from this collection alone.
        if original.startswith("Instruments / Percussion / Bells"):
            return "@BELLS", "low", "Publisher bell family; musical/non-musical use unspecified", "sfx"
        return {"Horns": "MUSCBrass", "Percussion": "MUSCPerc", "Strings": "MUSCStr", "Winds": "MUSCWind"}.get(subgroup, "@MUSICAL"), "medium", "Publisher instrument family; sample, not assumed full music", "sfx"
    if family == "Animals":
        # Mixed environmental descriptions should not become isolated vocalisations.
        ambience = match_rules(d, [(r"waves and seagulls", "AMBSea"), (r"stream with frog", "AMBRurl"),
            (r"barnyard|stable sounds|chkncoop|loudcoop", "AMBFarm"), (r"crickets at night", "AMBInsc"), (r"aviary", "AMBBird")])
        if ambience:
            return (*ambience, "ambience")
        if re.search(r"\btrot[23]?\b|horses gallop|horses on pavement", d):
            return "FEETHors", "medium", "Explicit horse gait description", "sfx"
        if " and " in d or "&" in d:
            return "@ANIMALS", "low", "Multiple animals named; no single leaf asserted", "sfx"
        hit = match_rules(d, ANIMALS)
        if hit:
            return (*hit, "sfx")
        return ("@BIRDS" if subgroup == "Birds" else "@ANIMALS"), "low", "Publisher family only; abbreviated or ambiguous description", "unknown"
    rules = HOUSE if family == "Household" else NATURE if family == "Nature" else PEOPLE if subgroup == "People" else []
    hit = match_rules(d, rules)
    if hit:
        return (*hit, "ambience" if hit[0].startswith("AMB") else "sfx")
    if subgroup == "Bounce/Spring":
        return "TOONBoing", "medium", "Publisher Bounce/Spring effects section", "sfx"
    if subgroup == "Electronic":
        return "DSGNSynth", "medium", "Publisher electronic effects section; precise game function unassigned", "sfx"
    extra = []
    if subgroup == "Glass":
        extra = [(r"bottle blow", "GLASTonl"), (r"beer into mug|water into cup", "FOODPour"), (r"shattered", "GLASBrk"), (r"glass", "@GLASS")]
    elif subgroup == "Military":
        extra = [(r"laser|lasershot|laserburst", "LASRGun"), (r"ricochet|rico2|caroming", "BLLTRico"),
            (r"chopper|helicopter", "AEROHeli"), (r"afterburner|after burner", "AEROJet"),
            (r"airplane", "@AIRCRAFT"), (r"air raid siren", "ALRMSirn"),
            (r"cannon", "GUNCano"), (r"machine gun|mach gun", "GUNAuto"),
            (r"explosion1|exp2|bomb hit", "@EXPLOSIONS"), (r"sonar", "COMTelm"),
            (r"gunshot|shooting1|semi-automatic", "@GUNS"), (r"bugle", "MUSCBrass")]
    elif subgroup == "Sirens/alarms/bells":
        extra = [(r"police siren", "VEHSirn"), (r"boat.*horn", "BOATHorn"), (r"whistle", "WHSTMech"),
            (r"clock ticking", "CLOCKTick"), (r"big ben|clock bell|clock toll", "CLOCKChim"),
            (r"churchbell|university bells|big bell", "BELLLrg"), (r"gong", "BELLGong"),
            (r"alarm bell|schoolbell", "ALRMBell"), (r"bell|bells", "@BELLS"), (r"alarm|alarming", "@ALARMS")]
    elif subgroup == "Sports":
        extra = [(r"crowd|crowdnoise", "CRWDSprt"), (r"bugle", "MUSCBrass"),
            (r"poker|playing cards|shuffle the deck", "GAMEBoard"),
            (r"baseball|ball hitting glove|batted ball|hitting bat|hole-in-one", "SPRTField"),
            (r"billiards|bowling|bowl a strike|gutter ball|pool|ping-pong", "SPRTIndor")]
    elif subgroup == "Tools":
        extra = [(r"old machinery", "MACHAntq"), (r"air-powered", "TOOLPneu"), (r"arc welder", "ELECArc"), (r"blow torch", "FIRETrch"),
            (r"chain dragging", "CHAINMvmt"), (r"chainsaw|electric saw|power saw", "TOOLPowr"),
            (r"lawn mower|hedge trimmer", "MACHGrdn"), (r"sprinkler", "WATRSpray"),
            (r"hammer on anvil", "METLImpt"), (r"socket wrench", "TOOLHand"),
            (r"conveyer", "MACHInd"), (r"hand-pump", "MACHPump"), (r"fire extinguisher", "AIRBrst")]
    elif subgroup == "Transportation":
        extra = [(r"737", "AEROJet"), (r"carhorn\d*|car horn|old horn", "VEHHorn"),
            (r"motorcycle", "VEHMoto"), (r"race car|hot rod", "VEHRace"),
            (r"studebaker", "VEHAntq"), (r"subway", "TRNSbwy"), (r"cablecar", "TRNTram"),
            (r"train", "@TRAINS"), (r"tire skid", "VEHSkid"), (r"truck brakes", "VEHBrake"),
            (r"car hood", "VEHMech"), (r"car warning", "BEEPVeh")]
    elif subgroup == "Misc":
        extra = [(r"coin|coins", "OBJCoin"), (r"castle door", "DOORAntq"), (r"jail door", "DOORPrisn"),
            (r"metal door", "DOORMetl"), (r"zipper", "OBJZipr"), (r"papers|pages", "PAPRHndl"),
            (r"whip", "WEAPWhip"), (r"whoosh|swoosh", "WHSH"), (r"swish", "SWSH"),
            (r"switch|switches|switchoff", "MECHSwtch"), (r"scraping metal", "METLFric"),
            (r"metal tap|striking metal", "METLImpt"), (r"wood dropping", "WOODImpt"),
            (r"lit match", "FIREIgn"), (r"printer|electric calculator", "MACHOffc"), (r"soft piano", "MUSCKeyd"),
            (r"velcro close|velcro open", "CLOTHRip"), (r"rewinding tape", "COMAv"),
            (r"knock on wood", "WOODImpt"), (r"winch", "MECHPuly"),
            (r"water sprayed", "WATRSpray"), (r"cash register", "MACHOffc"), (r"finch", "BIRDSong")]
    hit = match_rules(d, extra)
    if hit:
        return (*hit, "sfx")
    broad = "@SPORTS" if subgroup == "Sports" else "@TOOLS" if subgroup == "Tools" else "@HUMAN" if subgroup == "People" else None
    return broad, "low" if broad else "none", "Description needs listening/review; publisher folder retained", "unknown"

def make_record(path, root, description, original, source, label, ucs, **extra):
    target, confidence, reason, content = label
    catid = target if target and not target.startswith("@") else None
    category = target[1:] if target and target.startswith("@") else ucs[catid]["category"] if catid else None
    return dict(path=path.relative_to(root).as_posix(), description=description,
        original_category=original, catid=catid, category=category, confidence=confidence,
        reason=reason + "; provisional metadata label, not ear verified", content=content,
        metadata_source=source, **extra)

def decoded_sample_signature(path):
    """Preserve sample values and channel order; do not resample or downmix."""
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_name,sample_rate,channels,bits_per_sample,bits_per_raw_sample',
        '-of', 'json', str(path)], capture_output=True, check=True, timeout=40, creationflags=flags)
    stream = json.loads(probe.stdout)['streams'][0]
    bits = int(stream.get('bits_per_raw_sample') or stream.get('bits_per_sample') or 0)
    codec = stream.get('codec_name', '')
    if not codec.startswith('pcm_') or codec.startswith(('pcm_f', 'pcm_s64', 'pcm_u64')) or not 0 < bits <= 32:
        return None
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0',
        '-c:a', 'pcm_s32le', '-f', 'hash', '-hash', 'sha256', '-'],
        capture_output=True, check=True, timeout=180, creationflags=flags)
    match = re.fullmatch(r'SHA256=([0-9a-f]{64})\s*', decoded.stdout.decode('ascii'))
    if match is None:
        raise ValueError('Missing decoded sample hash: ' + str(path))
    return int(stream['sample_rate']), int(stream['channels']), match[1]

def read_wayzata(root, ucs, issues):
    library = root / WAYZATA
    source = library / "FILELIST.TXT"
    if not source.exists():
        return []
    files = {p.relative_to(library).as_posix().lower(): p for p in library.rglob("*") if p.is_file()}
    wav_keys = defaultdict(list)
    for rel, path in files.items():
        if rel.startswith("sounds/wav/"):
            wav_keys[canonical_key(path.relative_to(library / "SOUNDS" / "WAV").parts)].append(path)
    top = sub = top_pc = sub_pc = ""
    records, covered = [], set()
    mappings = defaultdict(list)
    for line_number, line in enumerate(source.read_text(encoding="cp1252").splitlines(), 1):
        wav = re.match(r"^\s*(.*?)\s+([^\s]+\.wav)\s*$", line, re.I)
        if not wav:
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) != 2 or line_number <= 2:
                continue
            if line.startswith(" "):
                sub, sub_pc = parts
            else:
                top, top_pc = parts
                sub = sub_pc = ""
            continue
        description, filename = wav.groups()
        original = " / ".join(x for x in (top, sub) if x)
        rel = "/".join(x for x in ("SOUNDS/WAV", top_pc, sub_pc, filename) if x).lower()
        path = files.get(rel)
        alias_used = False
        if path is None:
            requested_key = canonical_key(tuple(x for x in (top_pc, sub_pc, filename) if x))
            candidates = wav_keys.get(requested_key, [])
            # FILELIST flattens the on-disk percussion subfolders. Require a
            # unique exact normalized stem under that same named family.
            if not candidates and top == "Instruments" and sub == "Percussion":
                candidates = [p for k, paths in wav_keys.items() if k[:2] == requested_key[:2] and k[-1] == requested_key[-1] for p in paths]
            if len(candidates) == 1:
                path = candidates[0]
                alias_used = True
        if path is None:
            issues.append({"kind": "missing_wayzata_filelist_target", "line": line_number, "path": rel, "description": description})
            continue
        metadata = source.relative_to(root).as_posix() + f":line {line_number}"
        if alias_used:
            metadata += "; explicit folder alias/punctuation-normalized filename"
        label = wayzata_label(description, original)
        records.append(make_record(path, root, description, original, metadata, label, ucs))
        covered.add(path)
        mappings[canonical_key(path.relative_to(library / "SOUNDS" / "WAV").parts)].append((description, original, metadata, label))
    # Attach exact same folder/stem AIFF equivalents, without claiming deduplication.
    for rel, path in sorted(files.items()):
        if not (rel.startswith("sounds/aiff/") or rel.startswith("sounds/wav/")):
            continue
        if path in covered:
            continue
        with path.open("rb") as stream:
            header = stream.read(12)
        valid = header[:4] in (b"RIFF", b"RIFX") and header[8:12] == b"WAVE" or header[:4] == b"FORM" and header[8:12] in (b"AIFF", b"AIFC", b"8SVX")
        if not valid:
            issues.append({"kind": "unrecognised_audio_header", "path": path.relative_to(root).as_posix()})
            continue
        parts = path.relative_to(library / "SOUNDS").parts[1:]
        key = canonical_key(parts)
        # .IF1/.IF2 are collision/alternate legacy names: never treat their
        # equal stem as proof they share the .IFF or WAV description.
        matches = mappings.get(key, []) if path.suffix.lower() in (".iff", ".wav") else []
        if matches:
            for description, original, metadata, label in matches:
                records.append(make_record(path, root, description, original, metadata + "; explicit folder aliases and punctuation-normalized stem counterpart", label, ucs))
            continue
        original = " / ".join(FOLDER_NAMES.get(x.upper(), x.title()) for x in parts[:-1])
        description = path.stem.replace("_", " ").strip()
        label = wayzata_label(description, original)
        # Truncated filenames cannot inherit high confidence.
        label = (label[0], "low" if label[0] else "none", "Filename/folder fallback (not FILELIST-matched). " + label[2], label[3])
        records.append(make_record(path, root, description, original, "path: " + path.relative_to(root).as_posix(), label, ucs))
    # DIR_TEXT supplies full Macintosh display names, including entries absent
    # or differently named in FILELIST. A unique 7/8-character prefix inside
    # the exact publisher section is evidence for truncated fallback stems.
    # Preserve source fields used by existing review IDs; recovered text lives
    # in supplemental fields and determines only the proposed label.
    guide_sections = {'Household':'HOUSEHOL', 'Nature':'NATURE',
        'Spec Eff / Military':'MILITARY', 'Spec Eff / Misc':'MISC_SPE',
        'Spec Eff / Sirens/alarms/bells':'SIRENS',
        'Spec Eff / Transportation':'TRANSPOR'}
    guides = {}
    for original, guide_name in guide_sections.items():
        guide = library / 'DIR_TEXT' / (guide_name + '.TXT')
        if guide.is_file():
            guides[original] = [(line.strip(), guide.relative_to(root).as_posix()+f':line {number}')
                for number,line in enumerate(guide.read_text(encoding='cp1252').splitlines(),1) if line.strip()]
    for row in records:
        if row['category'] is not None or not row['metadata_source'].startswith('path: '):
            continue
        stem = re.sub(r'[^a-z0-9]', '', Path(row['path']).stem.lower())
        if not 6 <= len(stem) <= 8:
            continue
        candidates = [(description, evidence) for description,evidence in guides.get(row['original_category'], [])
            if re.sub(r'[^a-z0-9]', '', description.lower()).startswith(stem)]
        if len(candidates) != 1:
            continue
        description, evidence = candidates[0]
        label = wayzata_label(description, row['original_category'])
        if label[0] is None:
            continue
        enriched = make_record(root / row['path'], root, row['description'], row['original_category'],
            row['metadata_source'], (label[0], 'low', 'Unique truncated stem matched to publisher DIR_TEXT description: '+description, label[3]), ucs,
            publisher_description=description, supplemental_metadata_source=evidence)
        row.update(enriched)
    # Identical files occur in several publisher sections. Recover missing
    # instrument provenance only from exact SHA-256 identity, never a shared
    # name, approximate fingerprint or model similarity. Conflicting peer
    # leaves prevent propagation. Rechecked on every run; no database needed.
    instrument_peers = defaultdict(list)
    for row in records:
        if row['catid'] is None or not row['original_category'].startswith('Instruments'):
            continue
        digest = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
        instrument_peers[digest].append(row)
    for row in records:
        if row['category'] is not None:
            continue
        digest = hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
        peers = instrument_peers.get(digest, [])
        if not peers or len({(peer['catid'],peer['category']) for peer in peers}) != 1:
            continue
        peer = sorted(peers, key=lambda item:item['path'])[0]
        row.update(catid=peer['catid'], category=peer['category'], confidence=peer['confidence'],
            content=peer['content'], reason='Exact SHA-256-identical publisher instrument peer: '+peer['path']+'; source provenance recovered, not ear verified',
            duplicate_label_source=peer['path'], duplicate_label_sha256=digest)
    # These observed WAV/AIFF instrument variants preserve every decoded
    # integer sample and channel but declare different playback rates. This
    # establishes shared instrument provenance, not identical playback audio.
    rate_variant_peers = {
        'SOUNDS/WAV/HOUSE/DROPPED.WAV':'SOUNDS/AIFF/INSTRUME/ELECTRON/DROPPED.IFF',
        'SOUNDS/WAV/SPEC/MISC/RATTLER.WAV':'SOUNDS/AIFF/INSTRUME/PERCUSSI/MISC/RATTLER.IFF',
    }
    by_path = {row['path']:row for row in records}
    for relative, peer_relative in rate_variant_peers.items():
        row = by_path.get(WAYZATA + '/' + relative)
        peer = by_path.get(WAYZATA + '/' + peer_relative)
        if row is None or peer is None or row['category'] is not None or peer['catid'] is None:
            continue
        if not peer['original_category'].startswith('Instruments'):
            continue
        signature = decoded_sample_signature(root / row['path'])
        peer_signature = decoded_sample_signature(root / peer['path'])
        if signature is None or peer_signature is None or signature[1:] != peer_signature[1:]:
            continue
        row.update(catid=peer['catid'], category=peer['category'], confidence='low', content=peer['content'],
            reason='Identical decoded integer sample values and channel order to publisher instrument peer '+peer['path']+
                '; declared playback rates '+str(signature[0])+' versus '+str(peer_signature[0])+ 
                ' Hz differ, so speed/pitch/duration differ and this is not an exact playback duplicate; instrument provenance proposed, not ear verified',
            sample_value_label_source=peer['path'], sample_value_hash=signature[2],
            sample_value_channels=signature[1], source_sample_rate=signature[0],
            label_source_sample_rate=peer_signature[0])
    # These four QuickTime demonstrations contain audio tracks confirmed by
    # the catalogue scan. Other movie/help files are not assumed to have audio.
    # Technical audio properties remain supplied by the scan's source-path join.
    for filename in ('DOG.MOV', 'GOOD_BYE.MOV', 'LOGO.MOV', 'WELCOME.MOV'):
        path = files.get('qt_movie/' + filename.lower())
        if path is None:
            continue
        label = ('ANMLDog', 'low', 'Literal QuickTime audio-track filename DOG; provisional dog-source interpretation, action unspecified', 'sfx') if filename=='DOG.MOV' else (
            None, 'none', 'QuickTime audio-track title only; no publisher description establishes speech, music or another audible source', 'unknown')
        records.append(make_record(path, root, path.stem, 'QT_MOVIE',
            'path: ' + path.relative_to(root).as_posix(), label, ucs,
            source_kind='movie_audio_track', container_format='mov',
            label_status='provisional', audio_verified=False))
    return records

def universal_label(heading, description):
    description = description.upper()
    target = UNIVERSAL_MAP.get(heading)
    reason = "Reviewed publisher heading mapping; multi-index tracks are not segmented"
    if heading.startswith("AIRPLANE,") and heading != "AIRPLANE, CRASH":
        target = "AEROProp" if any(x in heading for x in ("PROP", "BIPLANE", "TRIPLANE")) else "@AIRCRAFT"
    if heading.startswith("BUZZER,"):
        target = "ALRMBuzr"
    if heading == "ARCHERY":
        target = "WEAPArro" if "ARROW" in description else "WEAPBow" if "BOW" in description else "@WEAPONS"
    if heading in ("GUN, HAND, FOLEY", "GUN, RIFLE, FOLEY", "GUN, MACHINE, FOLEY"):
        target = "GUNHndl" if any(x in description for x in ("DROP", "SHAKE", "SCABBARD")) else "GUNMech"
    if heading == "UNDERWATER" and any(x in description for x in ("AMBIENCE", "PRESENCE")):
        target = "AMBUndwtr"
    if heading == "ROCK":
        target = "ROCKCrsh" if any(x in description for x in ("SLIDE", "CRASH", "DEBRIS")) else "ROCKImpt" if any(x in description for x in ("HIT", "IMPACT", "DROP")) else "@ROCKS"
    if heading == "COMEDY":
        specific = match_rules(description, [(r"boing", "TOONBoing"), (r"stretch wire spring", "TOONStrch"),
            (r"slide whistle", "TOONWhis"), (r"twang", "TOONTwang")])
        if specific:
            target = specific[0]
    # The actual index action can be more specific than a publisher heading.
    # These overrides stay within the named family; generic material/scene
    # words deliberately do not trigger cross-library classification.
    if (heading.startswith("AIRPLANE,") and heading != "AIRPLANE, CRASH" or heading in ("HELICOPTER", "DIRIGIBLE")) and "INT:" in description:
        target = "AEROInt"
    if heading == "CRASH, DISHES" and "SMASH" in description:
        target = "GLASCrsh" if "GLASSES" in description else "CERMCrsh" if "TRAY" in description or "SCUFFLE" in description else "CERMBrk"
    if heading == "CRASH, CHINA":
        target = "CERMBrk"
    if heading == "CRASH, PIGGY BANK":
        target = "CERMBrk"
    if heading == "CRASH, MISCELLANEOUS" and "BLOCK OF ICE" in description:
        target = "ICEImpt"
    if heading == "BUCKET, METAL":
        target = "METLHndl"
    if heading == "CLICK":
        target = "DOORHdwr"
    if heading == "FIRE, AMBIENCE":
        target = "AMBEmrg"
    if heading == "EXPLOSION, JET" and "DECOMPRESS" in description:
        target = "AEROInt"
    if heading in ("HORN, ANTIQUE", "HORN, KLAXON", "HORN, BULB") and "AUTO" in description:
        target = "VEHHorn"
    if heading == "HORN, FOG":
        target = "HORNAir"
    if heading == "SIREN" and "POLICE OR AMBULANCE" in description:
        target = "VEHSirn"
    if heading == "GRIND, GEARS" and "AUTO" in description:
        target = "VEHMech"
    if heading == "RADIO, TUNING" and "STATIC" in description and "TUNING" not in description[len(heading):]:
        target = "COMStatic"
    if heading == "SPACE, GUN SHOTS":
        target = "LASRGun"
    if heading == "SPACE, ROBOT" and "WALKING" in description:
        target = "ROBTMvmt"
    if heading == "SPACE, SHIP" and "AMBIENCE" in description:
        target = "AMBSci"
    if heading == "BAZOOKA" and "EXPLOSION" in description:
        target = "@EXPLOSIONS"
    if heading == "DEPTH CHARGE" and "EXPLOD" not in description and "EXPLOSION" not in description:
        target = "WEAPMisc"
    if heading == "GUN, MACHINE GUN" and "BULLET IMPACTS" in description:
        target = "BLLTImpt"
    if heading == "WAGON" and "HOOVES ONLY" in description:
        target = "FEETHors"
    if heading == "INDIANS":
        target = "@AMBIENCE"
    # Clear index actions previously hidden by broad publisher headings.
    if heading.startswith("AIRPLANE,") and heading != "AIRPLANE, CRASH":
        if any(x in description for x in ("B-52", "B-17", "R5D", "FIGHTER SQUADRON")):
            target = "AEROInt" if "INT:" in description else "AEROMil"
    if heading == "AIRPLANE, CRASH":
        target = "DESTRCrsh"
    if heading == "ELECTRICITY":
        if "GENERATOR AND ARC MACHINE" in description or "TRANSFORMER ARCS" in description:
            target = "ELECArc"
        elif "SPARK GAP" in description:
            target = "ELECSprk"
        elif "HUM" in description:
            target = "ELECBuzz"
        elif "ARC BUZZ" in description:
            target = "ELECArc"
    if heading == "ROCK":
        if "SEVERAL ROCKS FALL" in description or "ROCK SPILL" in description:
            target = "ROCKCrsh"
        elif "SET DOWN" in description or "SINGLE ROCK FALL" in description or "BOUNCING" in description:
            target = "ROCKImpt"
        elif "TUMBLES" in description:
            target = "ROCKMvmt"
    if heading == "CLIMB, ICE":
        if "CHOPPING PICK AXE" in description or "KICKING CLAMPONS" in description:
            target = "ICEImpt"
        elif "CLIMBING GLACIER" in description or "APPROACHING" in description:
            target = "MOVEHmn"
    if heading == "HORN, ALERT" or heading == "HORN, KLAXON" and "ALARM" in description:
        target = "ALRMSirn"
    if heading == "WOOD, PRY":
        target = "WOODFric"
    if heading == "ROCKET":
        target = "AERORckt"
    if heading == "CROWD, CHANT":
        target = "CRWDCheer" if "CHEERING" in description else "@CROWDS"
    if heading == "EXPLOSION" and "PROCESSED" in description:
        target = "EXPLDsgn"
    if heading == "COMEDY":
        specific = match_rules(description, [
            (r"head bonk|head hit|hollow bonk|hollow donk", "TOONImpt"),
            (r"metal ping|brake drum clank", "TOONClang"),
            (r"drum and cymbal|piano hit|slide down and gong", "TOONMx"),
            (r"cork pop", "TOONPop"), (r"squeak|squeaky", "TOONSqk"),
            (r"camel honk|chimpanzee|laughing duck|parrot squawks", "TOONAnml"),
            (r"wind up motor|computer overload", "TOONMach"),
            (r"blowing nose|big slurp|big spit|spit into|licking|whoop", "TOONVox")])
        if specific:
            target = specific[0]
    if target != UNIVERSAL_MAP.get(heading):
        reason = "Reviewed publisher heading and explicit index action; multi-index tracks are not segmented"
    content = "ambience" if target and target.startswith("AMB") else "sfx" if target else "unknown"
    if heading == "INDIANS":
        content = "ambience"
    return target, "medium" if target and not target.startswith("@") else "low" if target else "none", reason, content

def read_universal(root, ucs, issues):
    from pypdf import PdfReader
    library = root / UNIVERSAL
    source = library / "tracklist.pdf"
    if not source.exists():
        return []
    tracks = {}
    for path in library.glob("*.mp3"):
        match = re.fullmatch(r"US\s*(\d+)\s*-\s*(\d+)\.mp3", path.name, re.I)
        if match:
            tracks[tuple(map(int, match.groups()))] = path
    records, covered = [], set()
    for page_number, page in enumerate(PdfReader(source).pages, 1):
        for line in page.extract_text().splitlines():
            if not line.startswith("US"):
                continue
            match = re.fullmatch(r"US(\d+)\s+(\d+)-(\d+)\s+(.+?)\s+(\d*):(\d{2})\s*", line)
            if not match:
                issues.append({"kind": "unparsed_universal_line", "page": page_number, "line": line})
                continue
            disc, track, index, description, minutes, seconds = match.groups()
            key = int(disc), int(track)
            path = tracks.get(key)
            if path is None:
                issues.append({"kind": "missing_universal_track", "disc": int(disc), "track": int(track), "entry_index": int(index)})
                continue
            heading = re.split(r"\s{3,}", description)[0].strip()
            normalized = re.sub(r"\s+", " ", description).strip()
            records.append(make_record(path, root, normalized, heading,
                source.relative_to(root).as_posix() + f":page {page_number}; US{disc} {track}-{index}",
                universal_label(heading, normalized), ucs, expected_duration=int(minutes or 0)*60+int(seconds), entry_index=int(index)))
            covered.add(path)
    for path in sorted(set(tracks.values()) - covered):
        records.append(make_record(path, root, path.stem, "", "filename", (None, "none", "No matching PDF entry", "unknown"), ucs))
    return records

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ucs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, help="Optional destination for validation report")
    args = parser.parse_args()
    root = args.root.resolve()
    ucs = {row["catid"]: row for row in json.loads(args.ucs.read_text(encoding="utf-8"))}
    categories = {row["category"] for row in ucs.values()}
    issues = []
    records = read_wayzata(root, ucs, issues) + read_universal(root, ucs, issues)
    for row in records:
        path = (root / row["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Invalid path: " + row["path"])
        if row["catid"] is not None and row["catid"] not in ucs:
            raise ValueError("Invalid UCS ID: " + row["catid"])
        if row["category"] is not None and row["category"] not in categories:
            raise ValueError("Invalid UCS category: " + row["category"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    report = {"rows": len(records), "unique_paths": len({row["path"] for row in records}),
        "by_library": dict(Counter(row["path"].split("/")[0] for row in records)),
        "confidence": dict(Counter(row["confidence"] for row in records)),
        "leaf_labelled": sum(row["catid"] is not None for row in records),
        "broad_only": sum(row["catid"] is None and row["category"] is not None for row in records),
        "unresolved": sum(row["category"] is None for row in records),
        "content": dict(Counter(row["content"] for row in records)), "issues": issues,
        "methodology": "Publisher metadata only. Reviewed heading/phrase mappings against supplied UCS. Broad and unresolved labels retained. Original audio untouched. Universal PDF durations are individual entry lengths, never inferred offsets. AIFF matched by explicit folder aliases and punctuation-normalized stems where possible; remaining names use low-confidence folder/filename inference. FILELIST flattens percussion folders; a unique same-stem match within that family is accepted. Legacy resource and SoundEdit formats are not decoded or label-propagated."}
    report_path = args.report or root / "_catalogue/work/structured_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("issues", "methodology")}, indent=2))
    print("Issues:", len(issues), "Report:", report_path)

if __name__ == "__main__":
    main()
