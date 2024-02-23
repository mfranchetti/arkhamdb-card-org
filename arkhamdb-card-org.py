# ArkhamDB Card Organisation
#
# Program to pull Arkham Horror:TCG card details
# from ArkhamDB.com, sort, organise and output
# to CSV.
# Used for maintaining binders or any other storage.
# It's a little bit flung together, may tidy up on the next pass.
#
# 2024-02-19    Initial version     Michael Franchetti

import json
import operator
import csv
import urllib.request

live = False # If True get fresh data from ArkhamDB, otherwise use local data
num_cores = 2
excluded_packs = ['rcore'] #, 'tskp', 'fhvp'}
excluded_packs = excluded_packs + ['nat', 'har', 'win', 'jac', 'ste'] # Investigator packs
excluded_cards = ['01000']  # Random basic weakness placeholder added by ArkhamDB
faction = {'guardian' : 1,
           'seeker' : 2,
           'rogue' : 3,
           'mystic' : 4,
           'survivor' : 5,
           'neutral' : 6,
           'multi' : 7,
           'mythos' : 8
           }
card_type = {'investigator' : 1,
             'asset' : 2,
             'event' : 3,
             'skill' : 4,
             'treachery' : 5,
             'enemy' : 6,
             'story' : 7,
             'location' : 8,
             }
slots_per_page = 18
cards_per_slot = 4

# Get source data
if live:
    with urllib.request.urlopen('https://arkhamdb.com/api/public/packs/') as url:
        packs = json.load(url)
    with open('packs.json', 'w') as f:
        json.dump(packs, f)
        f.close()
    with urllib.request.urlopen('https://arkhamdb.com/api/public/cards/') as url:
        cards = json.load(url)
    with open('cards.json', 'w') as f:
        json.dump(cards, f)
        f.close()
else:
    with open('packs.json', 'r') as f:
        packs = json.load(f)
        f.close()
    with open('cards.json', 'r') as f:
        cards = json.load(f)
        f.close()
    

# Packs data enrichment
# Add Cycle code and name to all packs
# Add sort field: cycle_position (##) position (##)
for p in packs:
    # Sort By (will be over written in a few cases)
    p['sort_by'] = (((p['cycle_position'] if 'cycle_position' in p else 99) * 100)
        + (p['position'] if 'position' in p else 99))
    # Old cycles
    if p['cycle_position'] < 8:
        for q in packs:
            if p['cycle_position'] == q['cycle_position'] and q['position'] == 1:
                p['cycle_code'] = q['code']
                p['cycle_name'] = q['name']
    # New cycles
    elif p['cycle_position'] < 50:
        for q in packs:
            if p['cycle_position'] == q['cycle_position'] and q['position'] == 1:
                p['cycle_code'] = q['code'][0:-1]
                p['cycle_name'] = q['name']
    # Return Tos
    elif p['cycle_position'] == 50:
        for q in packs:
            if p['position'] == q['cycle_position'] and q['position'] == 1:
                p['cycle_code'] = q['code']
                p['cycle_name'] = q['name']
                p['sort_by'] = (q['cycle_position'] * 100) + (3 if q['cycle_position'] == 1 else 8)
    # Investigators
    elif p['cycle_position'] == 60:
        p['cycle_code'] = 'gator'
        p['cycle_name'] = 'Investigators'
    # Stand-Alones
    elif p['cycle_position'] == 70:
        p['cycle_code'] = 'stand'
        p['cycle_name'] = 'Stand-alones'
    # Books
    elif p['cycle_position'] == 80:
        p['cycle_code'] = 'books'
        p['cycle_name'] = 'Books'
    # Print and Play
    elif p['cycle_position'] == 90:
        p['cycle_code'] = 'print'
        p['cycle_name'] = 'Parallel Investigators'
    # Other
    else:
        p['cycle_code'] = 'unkwn'

# Exclude unwanted cards
# Excluded decks
cards = [c for c in cards if c['pack_code'] not in excluded_packs]
# Excluded cards
cards = [c for c in cards if c['code'] not in excluded_cards]
# Mythos Cards
cards = [c for c in cards if c['faction_code'] != 'mythos']
# Story Cards
cards = [c for c in cards if c['type_code'] != 'story']
# Reverse side of cards, one entry only required
for c in cards:
    if c['code'][-1] == 'b':
        cards = [c for c in cards if c['code'][-1] != 'b']

# Cards data enrichment
# Add pack sort by field
#   Cycle ##
#   Pack ##
# Add card sort by field
#   Faction ##
#   Card Type ##
#   XP (0/1) #
#   XP (Value) #

for c in cards:
    # Add pack sort_by
    for p in packs:
        if c['pack_code'] == p['code']:
            c['pack_sort_by'] = p['sort_by']
            c['cycle_position'] = p['cycle_position']
            c['cycle_name'] = p['cycle_name']
    # Default if pack not identified
    if 'pack_sort_by' not in c:
        c['pack_sort_by'] = 9999
    # Increase card quantity for core set
    if c['pack_code'] == 'core' and c['type_code'] in ['asset','event','skill'] and 'restrictions' not in c:
        c['quantity'] = c['quantity'] * num_cores
    # Add total_quantity
    c['total_quantity'] = c['quantity']
    # Add display name
    if 'subname' in c:
        c['display_name'] = c['name'] + ': ' + c['subname']
    else:
        c['display_name'] = c['name']
    if 'xp' in c and c['xp'] > 0:        
            c['display_name'] = c['display_name'] + ' (' + str(c['xp']) + ')'
    # Add sort_name, strip punctuation and leading 'The'. Also leading 'A'?
    c['sort_name'] = c['display_name']
    if c['sort_name'][0:4] == 'The ':
        c['sort_name'] = c['sort_name'][4:]
    c['sort_name'] = ''.join(ch for ch in c['sort_name'] if ch.isalnum())
    # Add card sort by
    c['card_sort_by'] = 0
    # Move Weaknesses to End
    # Basic Weaknesses
    if 'subtype_code' in c and c['subtype_code'] == 'basicweakness':
        c['card_sort_by'] = (c['card_sort_by'] * 100) + 1
    # Weaknesses not Investigator Specific
    if c['type_code'] == 'treachery' and 'restrictions' not in c:
        c['card_sort_by'] = (c['card_sort_by'] * 100) + 2
    # Add Faction
    if 'faction2_code' in c:
        # Multi-class
        c['faction_code'] = 'multi'
        c['faction_name'] = 'Multi'
        c['card_sort_by'] = (c['card_sort_by'] * 100) + faction['multi']
    elif c['faction_code'] in faction:
        c['card_sort_by'] = (c['card_sort_by'] * 100) + faction[c['faction_code']]
    else:
        c['card_sort_by'] = (c['card_sort_by'] * 100) + 99
    # Add Card Type
    if c['type_code'] in card_type:
        c['card_sort_by'] = (c['card_sort_by'] * 100) + card_type[c['type_code']]
    else:
        c['card_sort_by'] = (c['card_sort_by'] * 100) + 99
    # Add XP (0/1)
    if 'xp' not in c or c['xp'] == 0:
        c['card_sort_by'] = (c['card_sort_by'] * 10)
        c['xp_req'] = False
    else:
        c['card_sort_by'] = (c['card_sort_by'] * 10) + 1
        c['xp_req'] = True
    # Combined sort
    c['combo_sort'] = str(c['card_sort_by']) + c['sort_name']

# Move subcards to separate list
gator_cards = [c for c in cards if 'restrictions' in c]
bonded_cards = [c for c in cards if 'bonded_to' in c]
# Remove subcards from main list
cards = [c for c in cards if 'restrictions' not in c]
cards = [c for c in cards if 'bonded_to' not in c]
# Add Investigator subcards
for c in cards:
    for g in gator_cards:
        if ((c['code'] in g['restrictions']['investigator'] and c['pack_code'] == g['pack_code']) or # Investigator Cards
            (c['cycle_position'] == 80 and c['pack_code'] == g['pack_code']) or # Book Alternates
            (c['cycle_position'] == 90 and c['pack_code'] == g['pack_code'])): # Parallel Investigators

            g['card_sort_by'] = c['card_sort_by']
            g['sort_name'] = c['sort_name'] + str(g['position'])
            g['parent_card'] = c['display_name']
            if 'subcards' in c:
                c['subcards'].append(g)
            else:
                c['subcards'] = [g]
            c['total_quantity'] += g['quantity']
            g['pack_code'] = ''
# Remove allocated cards from list  
gator_cards = [g for g in gator_cards if g['pack_code'] != '']

# Add Bonded subcards
# Sort cards so bonded cards are added to first eligible card
cards.sort(key=operator.itemgetter('card_sort_by', 'sort_name'))
for c in cards:
    if 'bonded_cards' in c:
        for cb in c['bonded_cards']:
            for b in bonded_cards:
                if cb['code'] == b['code']: 
                    b['card_sort_by'] = c['card_sort_by']
                    b['sort_name'] = c['sort_name'] + str(b['position'])
                    b['parent_card'] = c['display_name']
                    if 'subcards' in c:
                        c['subcards'].append(b)
                    else:
                        c['subcards'] = [b]
                    c['total_quantity'] += b['quantity']
                    b['code'] = ''
    # Repeat for sub cards. Currently only Luke Robinson.
    if 'subcards' in c:
        for sc in c['subcards']:
            if 'bonded_cards' in sc:
                for cb in sc['bonded_cards']:
                    for b in bonded_cards:
                        if cb['code'] == b['code']:
                            b['card_sort_by'] = c['card_sort_by']
                            b['sort_name'] = c['sort_name'] + str(b['position'])
                            b['parent_card'] = c['display_name']
                            c['subcards'].append(b)
                            c['total_quantity'] += b['quantity']
                            b['code'] = ''
# Remove allocated cards from list  
bonded_cards = [b for b in bonded_cards if b['code'] != '']

# Empower Self (Special case to put all Empower Self cards in one slot)
empower_self = ["06241","06242","06243"]
for c in cards:
    if c['code'] == empower_self[0]:
        for s in cards:
            if s['code'] in empower_self[1:]:
                s['parent_card'] = c['display_name']
                c['total_quantity'] += s['quantity']
                if 'subcards' in c:
                    c['subcards'].append(s)
                else:
                    c['subcards'] = [s]
cards = [c for c in cards if c['code'] not in empower_self[1:]]

# Add Customization cards
for c in cards:
    if 'customization_options' in c:
        t = {'cycle_name' : c['cycle_name'],
             'pack_name': c['pack_name'],
             'faction_name' : c['faction_name'],
             'quantity' : 3,
             'parent_card' : c['display_name'],
             'display_name' : c['name'] + ": Customization Options",
             'combo_sort' : c['combo_sort'],
             'card_sort_by' : c['card_sort_by'],
             'sort_name' : c['sort_name'],
             }
        if 'sub_cards' in c:
            c['subcards'].append(t)
        else:
            c['subcards'] = [t]
        c['total_quantity'] += 3

#Sort packs
packs.sort(key=operator.itemgetter('sort_by'))

# Open CSV and ouput packs
f = open('packs.csv', 'w', newline='', encoding='utf-8')
csv_file = csv.writer(f, delimiter='\t')
csv_file.writerow(['cycle_position',
                   'position',
                   'cycle_code',
                   'code',
                   'name',
                   'sort_by'
                  ])
for p in packs:
    csv_file.writerow([p['cycle_position'],
                       p['position'],
                       p['cycle_code'] if 'cycle_code' in p else None,
                       p['code'],
                       p['name'],
                       p['sort_by'] if 'sort_by' in p else None,
                      ])

f.close()

# Sort
cards.sort(key=operator.itemgetter('card_sort_by', 'sort_name'))

# Add page_number and page_slot
cur_faction = ''
cur_type = ''
cur_xp_req = False
page_number = 0
page_slot = 0
new_page = False
for c in cards:
    # Add fields
    c['page_number'] = []
    c['page_slot'] = []
    # Get quantity
    qty = c['total_quantity']
    # Update page_number and card_slot
    while qty > 0:
        if c['faction_code'] != cur_faction:
            cur_faction = c['faction_code']
            new_page = True
        if c['type_code'] != cur_type:
            cur_type = c['type_code']
            new_page = True
        if c['xp_req'] != cur_xp_req:
            cur_xp_req = c['xp_req']
            new_page = True
        if page_slot < slots_per_page:
            page_slot += 1
        else:
            new_page = True
        if new_page:
            page_number += 1
            page_slot = 1
            new_page = False
        # Add data
        if page_number not in c['page_number']:
            c['page_number'].append(page_number)
        if page_slot not in c['page_slot']:
            c['page_slot'].append(page_slot)
        # Adjust quantity
        qty -= cards_per_slot
    # Convert to string
    c['page_number'] = ','.join(map(str, c['page_number']))
    c['page_slot'] = ','.join(map(str, c['page_slot']))

# Open CSV and ouput cards
card_output = {'Cycle' : 'cycle_name',
               'Set' : 'pack_name',
               'Card Number' : 'position',
               'Class' : 'faction_name',
               'Type' : 'type_name',
               'Subtype' : 'subtype_name',
               'XP' : 'xp',
               'Quantity' : 'quantity',
               'Total Quantity' : 'total_quantity',
               'Linked to' : None,
               'Name' : 'display_name',
               'Page' : 'page_number',
               'Slot' : 'page_slot',
               'Sort' : 'combo_sort',
               }
subcard_output = {'Cycle' : 'cycle_name',
                  'Set' : 'pack_name',
                  'Card Number' : 'position',
                  'Class' : 'faction_name',
                  'Type' : 'type_name',
                  'Subtype' : 'subtype_name',
                  'XP' : 'xp',
                  'Quantity' : 'quantity',
                  'Total Quantity' : None,
                  'Linked to' : 'parent_card',
                  'Name' : 'display_name',
                  'Page' : None,
                  'Slot' : None,
                  'Sort' : 'combo_sort',
                  }
f = open('cards.csv', 'w', newline='', encoding='utf-8')
csv_file = csv.writer(f, delimiter='\t')
# Header
csv_file.writerow(list(card_output.keys()))
# Cards
for c in cards:
    row = []
    for key, value in card_output.items():
        row.append(c[value] if value in c else None)
    csv_file.writerow(row)
    if 'subcards' in c:
        for s in c['subcards']:
            subrow = []
            for key, value in subcard_output.items():
                subrow.append(s[value] if value in s else None)
            csv_file.writerow(subrow)


f.close()

# Print errors
if len(gator_cards) > 0:
    print('WARNING: Unallocated Investigator cards.')
    print(json.dumps(gator_cards, indent=4))
if len(bonded_cards) > 0:
    print('WARNING: Unallocated Bonded cards.')
    print(json.dumps(bonded_cards, indent=4))


