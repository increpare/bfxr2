"""Provisional metadata-only labels for Cinematic Sound Design and 500 Noises.

No audio is listened to, uploaded, renamed or changed. Interpretations of the
8.3 names are explicitly marked and never presented as publisher descriptions.
No guide expands those names: BBB/CCC/DDD.TXT are DOS directory listings only.
Big Fish's included Readme identifies the library as crafted cinematic elements.
Run with --root --ucs --output. Uses only the Python standard library.
"""
import argparse
import collections
import json
from pathlib import Path
import re

CINEMATIC = 'Big Fish Audio - Cinematic Sound Design'
NOISES = 'Q45700 - 500 Noises'
AUDIO = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif', '.m4a'}

# Exact observed code families, with numeric variant suffixes removed only when
# explicitly allowed below. Do not apply loose substring/synonym matching here.
# Tuples: proposed interpretation, leaf (or None), broad category (or None),
# content. A code alone does not establish material, recording method or action.
NOISE_MAP = {}


def code(names, description, catid=None, category=None, content='sfx'):
    for name in names.split():
        if name in NOISE_MAP:
            raise ValueError('Duplicate code: ' + name)
        NOISE_MAP[name] = (description, catid, category, content)


code('747INT AIRINT', 'Aircraft interior', 'AEROInt')
code('AIR747', 'Boeing 747 aircraft', 'AEROJet')
code('AIRF14 AIRF15 AIRF18', 'Military aircraft', 'AEROMil')
code('AIRPL1', 'Aircraft', category='AIRCRAFT')
code('AIRHRN', 'Air horn', 'HORNAir')
code('ADDMAC', 'Adding machine', 'MACHOffc')
code('ALRM', 'Alarm; type unspecified', category='ALARMS')
code('ANVIL ANVILS', 'Anvil; action unspecified', category='METAL')
code('APLSMD APLSSM', 'Crowd applause', 'CRWDApls')
code('AXEHOR BLBHRN', 'Horn; subtype uncertain', category='HORNS')
code('BALLON', 'Balloon; action unspecified', category='RUBBER')
code('BASBAL', 'Baseball', 'SPRTField')
code('BBALLA BBALLB BBALLH', 'Basketball', 'SPRTCourt')
code('BEEP BEEPER', 'Beep; source unspecified', 'BEEP')
code('BEEROP', 'Beer container opening', category='FOOD & DRINK')
code('BEERPO WINEPR', 'Beer or wine pouring', 'FOODPour')
code('BELL', 'Bell; type unspecified', category='BELLS')
code('BELSL', 'Sleigh bells', 'MUSCBell')
code('BELTR', 'Bell; TR abbreviation unresolved', category='BELLS')
code('BIRD BIRDS', 'Bird vocalization; species unspecified', category='BIRDS')
code('BOILNG', 'Boiling; liquid/source unspecified', category='LIQUID & MUD')
code('BONFYR', 'Bonfire', 'FIREBurn')
code('BOWLNG', 'Bowling', 'SPRTIndor')
code('BUBLBG BUBLSM', 'Bubbles; liquid unspecified', 'LIQBubl')
code('BUCKET', 'Bucket; action unspecified', 'OBJCont')
code('BUGLE', 'Bugle', 'MUSCBrass')
code('BURNER', 'Burner; action unspecified', category='FIRE')
code('BUSAWY BUSPU', 'Bus movement', 'VEHBus')
code('BUZZER', 'Buzzer', 'ALRMBuzr')
code('CAMERA', 'Camera', 'COMCam')
code('CANCLS CANCRU CANDRP CANOP1 CANOPN CANPOR',
     'Can/container; material and contents unspecified', 'OBJCont')
code('CANNON', 'Cannon', 'GUNCano')
code('CARBF1 CARBF2', 'Car backfire', 'VEHCar')
code('CARDRC CARDRO', 'Car door closing or opening', 'VEHDoor')
code('CARHN', 'Car horn', 'VEHHorn')
code('CASINO', 'Casino', 'GAMECas')
code('CAT', 'Cat', 'ANMLCat')
code('CAVE', 'Cave environment', 'AMBUndr', content='ambience')
code('CHAIN', 'Chain; action unspecified', category='CHAINS')
code('CHERLG CHERSM', 'Crowd cheering', 'CRWDCheer')
code('CHILDN', 'Children; activity unspecified', category='VOICES', content='unknown')
code('CHNSAW', 'Chainsaw', 'TOOLPowr')
code('CITY CTYOLD', 'City environment', 'AMBUrbn', content='ambience')
code('CIVWAR WW2 WAR', 'Warfare environment', 'AMBWar', content='ambience')
code('CLOCK', 'Clock; action unspecified', category='CLOCKS')
code('CMOUSE COMKEY', 'Computer mouse or keyboard', 'CMPTKey')
code('COINC1 COINC2 COINCA COINCN COINDP COINDR COINLG COINMN COINS COINSM COINWD',
     'Coins', 'OBJCoin')
code('COMBEP', 'Computer beep', 'BEEP')
code('COPTER', 'Helicopter', 'AEROHeli')
code('CORK', 'Cork; action unspecified', category='FOOD & DRINK')
code('CORVPA CORVPB CORVPU', 'Corvette car movement', 'VEHCar')
code('COW', 'Cow', 'ANMLFarm')
code('CRDAMB', 'Crowd environment', category='CROWDS', content='ambience')
code('CRDBOO', 'Crowd booing', 'CRWDReac')
code('CRDEXT CRDPTY', 'Crowd; reaction/activity unspecified', category='CROWDS')
code('CRDLF', 'Crowd laughter', 'CRWDLaff')
code('CRDMAD', 'Angry crowd', 'CRWDAngr')
code('CRDMUR', 'Crowd murmuring', 'CRWDWalla')
code('CRDYLP', 'Crowd yelping', 'CRWDReac')
code('CSHRG', 'Cash register', 'MACHOffc')
code('CRTNCL CRTNOP', 'Curtain closing or opening', 'WNDWCover')
code('CUFFS', 'Handcuffs', 'EQUIPTact')
code('CURLNG', 'Curling', 'SPRTWntr')
code('DBELL', 'Doorbell', 'BELLDoor')
code('DCKCLL', 'Duck call; live bird versus imitation unspecified', category='BIRDS')
code('DINO', 'Dinosaur', 'CREADino')
code('DOGDRK DOGL DOGM DOGPAN', 'Dog vocalization or panting', 'ANMLDog')
code('DOOR', 'Door opening or closing; material unspecified', category='DOORS')
code('DRONE', 'Drone; source unspecified', category='DESIGNED')
code('DRWRCL DRWROP', 'Drawer closing or opening; material unspecified', category='DRAWERS')
code('DSHWSH', 'Dishwasher', 'MACHAppl')
code('ELECTR', 'Electricity; action unspecified', category='ELECTRICITY')
code('ELEVAT', 'Elevator', 'MACHElev')
code('EXPLO', 'Explosion; real versus designed unspecified', category='EXPLOSIONS')
code('FARM', 'Farm environment', 'AMBFarm', content='ambience')
code('FBCTCH FBKCK', 'Football catching or kicking', 'SPRTField')
code('FILECL FILEOP', 'Filing cabinet opening or closing', 'DOORCab')
code('FILMP', 'Film projector', 'COMAv')
code('FIREST', 'Fire starting', 'FIREIgn')
code('FOOTS', 'Footsteps; walker unspecified', category='FOOTSTEPS')
code('FRDGC FRDGO', 'Refrigerator door closing or opening', 'DOORAppl')
code('FRKLDN FRKLFT FRKLUP', 'Forklift', 'VEHUtil')
code('FROGS', 'Frogs', 'ANMLAmph')
code('FURNAC', 'Furnace', 'MACHHvac')
code('FYRTRK', 'Fire truck', 'VEHEmrg')
code('GASCAN', 'Gas can; action unspecified', 'OBJCont')
code('GASFIL', 'Fuel filling', category='LIQUID & MUD')
code('GAVEL', 'Gavel', 'TOOLHand')
code('GCANCL GCANOP', 'Garbage can closing or opening', 'OBJCont')
code('GOLF PUTT', 'Golf', 'SPRTField')
code('GONG', 'Gong', 'BELLGong')
code('GUNCOK GUNDRY GUNSLC GUNSLD GUNSPN RFLLVR SGUNAC', 'Gun mechanism', 'GUNMech')
code('GUNSHT', 'Gunshot; gun type unspecified', category='GUNS')
code('HARP', 'Harp', 'MUSCPluck')
code('HATCHC HATCHO', 'Hatch closing or opening; material/location unspecified', category='DOORS')
code('HEARTM', 'Heart monitor', 'BEEPMed')
code('HIWAY TRFJAM', 'Road traffic environment', 'AMBTraf', content='ambience')
code('HOCKEY SLPSHT', 'Hockey or slapshot', 'SPRTWntr')
code('HOISTD HOISTU', 'Hoist lowering or raising', category='MACHINES')
code('HORROR SPOOKY', 'Horror/spooky designed effect', 'DSGNErie')
code('HRSAWY HRSBY HRSUP', 'Horse movement; gait unspecified', 'FEETHors')
code('HRSNRT HRSWIN', 'Horse snort or whinny', 'ANMLHors')
code('HRSRAC', 'Horse racing', category='SPORTS')
code('ICECUB', 'Ice cubes; action unspecified', category='ICE')
code('ICEDRP', 'Ice drop', 'ICEImpt')
code('IMPWRN', 'Impact wrench', 'TOOLPowr')
code('INDYCR', 'Indy racing car', 'VEHRace')
code('JUGSHK', 'Jug shaking', 'OBJCont')
code('JUNGLE', 'Jungle environment', 'AMBTrop', content='ambience')
code('KETTLE', 'Kettle; action unspecified', category='FOOD & DRINK')
code('KEYS', 'Keys', 'OBJKey')
code('KNIFE', 'Knife; context unspecified', category='TOOLS')
code('LAKE', 'Lake environment', 'AMBLake', content='ambience')
code('LASER', 'Laser; action unspecified', category='LASERS')
code('LEPARD', 'Leopard', 'ANMLWcat')
code('LOCK ULOCK', 'Lock or unlock mechanism', 'MECHLock')
code('MBOXCL MBOXOP', 'Mailbox closing or opening', 'OBJCont')
code('MCHGUN MGUNBT', 'Machine gun', 'GUNAuto')
code('MCYCL', 'Motorcycle', 'VEHMoto')
code('MDEVAL OLDWST', 'Historical environment', 'AMBHist', content='ambience')
code('MUDBUB', 'Mud bubbles', 'LIQBubl')
code('MUSC', 'Music; form unspecified', category='MUSICAL', content='music')
code('OCEAN', 'Ocean; action unspecified', category='WATER', content='unknown')
code('OFFICE', 'Office environment', 'AMBOffc', content='ambience')
code('OWL', 'Owl', 'BIRDPrey')
code('PHNHNG PHNPUP PHONH1 PHONP1 PHONR', 'Telephone handling or ringing', 'COMTelph')
code('PIG', 'Pig', 'ANMLFarm')
code('PLNGER', 'Plunger; action unspecified', category='TOOLS')
code('PNGPON', 'Ping pong', 'SPRTIndor')
code('PNO', 'Piano', 'MUSCKeyd')
code('POTPAN', 'Pots and pans', 'FOODKware')
code('RCKCHR', 'Rocking chair', 'OBJFurn')
code('RFLSHT', 'Rifle shot', 'GUNRif')
code('RIP TEAR', 'Ripping/tearing; material unspecified', content='unknown')
code('RIVER', 'River flow', 'WATRFlow')
code('ROLLRB', 'Rollerblading', 'SPRTSkate')
code('SAFECL SAFEOP', 'Safe closing or opening', category='DOORS')
code('SGUNSH', 'Shotgun shot', 'GUNShotg')
code('SHIP', 'Ship; activity unspecified', 'BOATShip')
code('SHOWER TOILET TUB', 'Shower, toilet or bathtub plumbing', 'WATRPlmb')
code('SHPBEL', 'Ship bell; bell type unspecified', category='BELLS')
code('SHPCRK', 'Ship creaking', 'BOATMech')
code('SIREN', 'Siren; source unspecified', 'ALRMSirn')
code('SLOTM', 'Slot machine', 'GAMECas')
code('SOCCER', 'Soccer', 'SPRTField')
code('SPACE', 'Space-themed effect; activity unspecified', category='SCIFI')
code('SPRAY SPRAY2 SPRAYS SPRITZ SPRYON', 'Spray; substance/source unspecified', content='unknown')
code('SQUASH', 'Squash; sport versus squashing action unresolved', content='unknown')
code('STAPLE', 'Stapler', 'OBJOffc')
code('STOCK', 'Stock car', 'VEHRace')
code('STPWCH', 'Stopwatch; action unspecified', category='CLOCKS')
code('SWTCH', 'Switch', 'MECHSwtch')
code('SYNTH', 'Synthesized sound; musical versus designed role unresolved', 'DSGNSynth')
code('TBLSAW', 'Table saw', 'TOOLPowr')
code('TELTYP', 'Teletype', 'COMTelm')
code('TENNIS VBALL', 'Tennis or volleyball', 'SPRTCourt')
code('THUND', 'Thunder', 'THUN')
code('TIMP', 'Timpani', 'MUSCTnprc')
code('TOSTDN TOSTUP', 'Toaster lowering or popping up', 'MACHAppl')
code('TUGHRN', 'Tugboat horn', 'BOATHorn')
code('TYPING', 'Typing; keyboard versus typewriter unspecified', content='unknown')
code('UNWAT', 'Underwater; activity unspecified', 'WATRUndwtr')
code('VIBE1 VIBSLP', 'Vibraphone or vibraslap', category='MUSICAL')
code('WHIP', 'Whip; action unspecified', 'WEAPWhip')
code('WHOSH', 'Whoosh; natural versus designed unspecified', category='SWOOSHES')
code('WIND', 'Wind', 'WIND')
code('RAIN', 'Rain', 'RAIN')
code('XMAS', 'Christmas-themed; audible content unspecified', content='unknown')

# Further exact observed families. Short codes retain low confidence and an
# explicit interpretation, and unspecified materials are never invented.
NEW_NOISE_FAMILIES = set()
_previous_families = set(NOISE_MAP)
code('AIRREG', 'Air regulator; mechanism subtype unspecified', category='MECHANICAL')
code('CDYBOP CDYDRM CMDYCL CMDYDR CMDYX1 CMDYX2 CMDYX3',
     'Comedy effect; exact action unspecified', category='CARTOON')
code('CDYHRN', 'Comedy horn', 'TOONHorn')
code('CRDFLP CRDSHF', 'Playing cards flipping or shuffling', 'GAMEMisc')
code('CRASH1 CRASH2 CRSHBG CRSHLN CRSHSH CRSHSM SMASH1 SMASH2 SMASH3 SMASH4',
     'Crash or smash; source/material unspecified', category='DESTRUCTION')
code('FTHROW', 'Flamethrower', 'FIREBrst')
code('MARCH', 'Marching footsteps', 'FEETHmn')
code('PARADE', 'Parade environment; constituent sounds unspecified', category='AMBIENCE', content='ambience')
code('PEPGRN', 'Pepper grinding', 'FOODCook')
code('PNCSHP', 'Pencil sharpener', 'MACHOffc')
code('STONE', 'Stone; action unspecified', category='ROCKS')
code('STRBEL', 'Bell; STR abbreviation unresolved', category='BELLS')
code('SWMAMB', 'Swimming ambience', 'AMBSprt', content='ambience')
code('WHOOP', 'Whoop vocalization; speaker/action unspecified', category='VOICES')
code('CBASS1 CBASS2', 'Bass element; instrument and function unspecified', category='MUSICAL')
code('FLTLYN', 'Flatline monitor tone', 'BEEPMed')
code('BREW', 'Brewing; preparation sound, exact beverage unspecified', category='FOOD & DRINK')
code('STUMBL HOPPIN', 'Stumbling or hopping movement; actor unspecified', category='MOVEMENT')
code('SLIMEY', 'Slimy or viscous substance; action and exact material unspecified', category='LIQUID & MUD')
NEW_NOISE_FAMILIES = set(NOISE_MAP) - _previous_families

# Numeric suffix normalization is opt-in, including DOOR/LOCK C/O variants.
NUMBERED = {'ALRM', 'BELL', 'BELSL', 'BELTR', 'CARHN', 'CORK', 'CRDLF',
            'CSHRG', 'CUFFS', 'DBELL', 'DOOR', 'DRONE', 'EXPLO', 'FOOTS',
            'FRDGC', 'FRDGO', 'GOLF', 'GONG', 'HARP', 'KEYS', 'KNIFE',
            'LASER', 'LOCK', 'MCYCL', 'MUSC', 'PHONR', 'PNO', 'SIREN',
            'STOCK', 'SWTCH', 'SYNTH', 'TEAR', 'THUND', 'TIMP', 'TUB',
            'ULOCK', 'UNWAT', 'WHOSH'}


def noise_label(stem):
    raw = stem.upper()
    short = raw[2:] if raw.startswith('16') else raw
    family = short
    if family not in NOISE_MAP:
        match = re.fullmatch(r'([A-Z]+)\d+[CO]?', short)
        if match and match[1] in NUMBERED:
            family = match[1]
    mapped = NOISE_MAP.get(family)
    if mapped is None:
        return raw, None, None, 'none', 'unknown', (
            'Unexpanded 8.3 filename code; no supplied descriptive guide or '
            'standard RIFF description. Audible source remains unresolved.')
    description, catid, category, content = mapped
    # Existing source descriptions participate in stable review identities.
    # New interpretations enrich reason, without rewriting their raw titles.
    display = raw if family in NEW_NOISE_FAMILIES else raw + ' — ' + description + ' (filename interpretation)'
    return (display, catid,
            category, 'low' if catid or category else 'none', content,
            'Provisional interpretation of exact observed code family ' + family +
            '; proposed meaning: ' + description +
            '; the shortened name has no publisher expansion. Not audio-verified.')


def cinematic_label(stem, folder):
    text = stem.lower()
    # Function/folder context takes precedence over ingredients such as metal,
    # wind, bells, voices or a monster: these are layered cinematic elements.
    if folder == 'Atmospheric Beds':
        return 'AMBDsgn', 'ambience', 'Publisher atmospheric-bed folder; crafted cinematic soundscape.'
    if folder == 'Drones':
        return 'DSGNDron', 'sfx', 'Publisher drone folder; sustained designed element.'
    if folder in {'Cinematic Hits', 'Complex Hits'}:
        return 'DSGNImpt', 'sfx', 'Publisher cinematic/complex-hit folder; designed impact, including processed ingredients.'
    if folder == 'Explosions':
        return 'EXPLDsgn', 'sfx', 'Explosion hit/blast in a crafted cinematic library; no claim of a real explosion recording.'
    if folder == 'Distortions':
        return 'DSGNDist', 'sfx', 'Publisher distortion folder; distortion is the principal designed treatment.'
    if folder == 'Risers':
        return 'DSGNRise', 'sfx', 'Publisher riser folder; cinematic tension rise.'
    if folder in {'Whooshes', 'Hit To Whoosh', 'Whoosh To Hit'}:
        return 'DSGNWhsh', 'sfx', 'Publisher whoosh/impact-transition folder; stylized cinematic movement.'
    if 'whoosh' in text or ('Metal Scrapes' == folder and re.search(r'pass\s*by|swirl', text)):
        return 'DSGNWhsh', 'sfx', 'Filename names a processed whoosh/pass-by/swirl in the cinematic library.'
    if folder == 'Reverses':
        # Reverse playback does not alone prove a pitch riser or raw source.
        return None, 'sfx', 'Reverse/suction treatment specified; precise designed leaf needs listening.'
    if folder == 'Metal Scrapes':
        if re.search(r'ghostly|eerie', text):
            return 'DSGNErie', 'sfx', 'Filename explicitly names an eerie designed scrape; raw material is not asserted.'
        return None, 'sfx', 'Processed cinematic metal scrape; no claim of an unprocessed friction recording.'
    if re.search(r'\bhit\b|\bslam\b', text):
        return 'DSGNImpt', 'sfx', 'Filename explicitly describes a cinematic hit/slam.'
    if 'rumble' in text:
        return 'DSGNRmbl', 'sfx', 'Filename explicitly describes a designed rumble.'
    if re.search(r'feedback|static|fuzz', text):
        return 'DSGNDist', 'sfx', 'Filename explicitly describes feedback/static/fuzz as a designed effect.'
    return None, 'sfx', 'Crafted cinematic element; title insufficient for a precise designed leaf.'


def rows(root, ucs):
    for library in (CINEMATIC, NOISES):
        folder = root / library
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob('*'), key=lambda p: p.as_posix().casefold()):
            if not path.is_file() or path.suffix.lower() not in AUDIO:
                continue
            original_category = path.parent.relative_to(folder).as_posix()
            if library == CINEMATIC:
                catid, content, reason = cinematic_label(path.stem, original_category)
                description = path.stem
                category = ucs[catid]['category'] if catid else 'DESIGNED'
                confidence = 'medium' if catid else 'low'
                source = 'filename+parent_directory+included_readme_library_context'
            else:
                description, catid, category, confidence, content, reason = noise_label(path.stem)
                if catid:
                    category = ucs[catid]['category']
                source = 'abbreviated_filename+parent_directory'
            yield {'path': path.relative_to(root).as_posix(),
                   'description': description, 'original_category': original_category,
                   'catid': catid, 'category': category, 'confidence': confidence,
                   'reason': reason, 'content': content, 'metadata_source': source,
                   'label_status': 'provisional', 'audio_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--ucs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.ucs.read_text(encoding='utf-8-sig'))
    ucs = {item['catid']: item for item in data}
    categories = {item['category'] for item in data}
    result = list(rows(args.root, ucs))
    if len({row['path'] for row in result}) != len(result):
        raise ValueError('Duplicate paths')
    for row in result:
        if not (args.root / row['path']).is_file():
            raise ValueError('Missing source: ' + row['path'])
        if row['catid'] is not None and row['catid'] not in ucs:
            raise ValueError('Unknown UCS ID: ' + row['catid'])
        if row['category'] is not None and row['category'] not in categories:
            raise ValueError('Unknown UCS category: ' + row['category'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n'
                                  for row in result), encoding='utf-8')
    counts = collections.Counter((row['path'].split('/')[0],
                                  'leaf' if row['catid'] else 'broad' if row['category'] else 'unresolved')
                                 for row in result)
    print(json.dumps({'files': len(result), 'counts': {' / '.join(k): v
                     for k, v in sorted(counts.items())}}, indent=2))


if __name__ == '__main__':
    main()
