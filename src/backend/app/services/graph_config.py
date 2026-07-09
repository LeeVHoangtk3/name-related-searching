ALLOWED_HUB_CLASSES = {
    "Q43229",   # organization
    "Q783794",  # company
    "Q7278",    # political party
    "Q476028",  # football club
    "Q133311",  # sports club
    "Q3918",    # university
    "Q7188",    # government
    "Q4164871", # position
}

# Các thuộc tính không liên quan hoặc là các ID ngoài (external identifiers/metadata) cần loại bỏ
# External identifiers and garbage properties to exclude
BLACKLIST_PROPERTIES = {
    "P281",   # postal code
    "P214",   # VIAF ID
    "P244",   # Library of Congress ID
    "P268",   # BNF ID
    "P269",   # SUDOC ID
    "P349",   # NDL ID
    "P906",   # Czech National Library ID
    "P1006",  # Dutch author ID
    "P1953",  # National Library of Spain ID
    "P227",   # GND ID
    "P1417",  # Encyclopædia Britannica Online ID
    "P3212",  # ISMN
    "P1015",  # NORAF ID
    "P3035",  # ISBN
    "P2671",  # Google Knowledge Graph ID
    "P1813",  # short name
    "P957",   # ISBN-10
}

# Các thuộc tính cốt lõi liên kết tri thức quan trọng
# Core semantic properties
PRIORITY_PROPERTIES = {
    "P106",   # occupation
    "P19",    # place of birth
    "P27",    # country of citizenship
    "P40",    # child
    "P22",    # father
    "P25",    # mother
    "P26",    # spouse
    "P3373",  # sibling
    "P108",   # employer
    "P39",    # office held
    "P69",    # educated at
}

# Ánh xạ thuộc tính đối ngẫu nghịch đảo để hiển thị nhãn chính xác khi đi ngược
# Reciprocal inverse property mappings
INVERSE_PROPERTIES = {
    "P40": "P22",    # child -> parent (father/mother)
    "P22": "P40",    # father -> child
    "P25": "P40",    # mother -> child
    "P26": "P26",    # spouse -> spouse
    "P3373": "P3373" # sibling -> sibling
}
