"""Static team catalog used for favorite team selection."""

from typing import Dict, List

# Each team entry exposes a primary value (stored in config), a display label,
# the common league abbreviation, and a small set of aliases to help match
# existing configs that may already use nicknames or abbreviations.

LeagueCatalog = Dict[str, Dict[str, object]]

TEAM_CATALOG: LeagueCatalog = {
    "nba": {
        "name": "NBA",
        "teams": [
            {
                "label": "Atlanta Hawks",
                "value": "atlanta hawks",
                "abbreviation": "ATL",
                "aliases": ["atlanta hawks", "hawks", "atl"],
            },
            {
                "label": "Boston Celtics",
                "value": "boston celtics",
                "abbreviation": "BOS",
                "aliases": ["boston celtics", "celtics", "bos"],
            },
            {
                "label": "Brooklyn Nets",
                "value": "brooklyn nets",
                "abbreviation": "BKN",
                "aliases": ["brooklyn nets", "nets", "bkn"],
            },
            {
                "label": "Charlotte Hornets",
                "value": "charlotte hornets",
                "abbreviation": "CHA",
                "aliases": ["charlotte hornets", "hornets", "cha"],
            },
            {
                "label": "Chicago Bulls",
                "value": "chicago bulls",
                "abbreviation": "CHI",
                "aliases": ["chicago bulls", "bulls", "chi"],
            },
            {
                "label": "Cleveland Cavaliers",
                "value": "cleveland cavaliers",
                "abbreviation": "CLE",
                "aliases": ["cleveland cavaliers", "cavaliers", "cavs", "cle"],
            },
            {
                "label": "Dallas Mavericks",
                "value": "dallas mavericks",
                "abbreviation": "DAL",
                "aliases": ["dallas mavericks", "mavericks", "mavs", "dal"],
            },
            {
                "label": "Denver Nuggets",
                "value": "denver nuggets",
                "abbreviation": "DEN",
                "aliases": ["denver nuggets", "nuggets", "den"],
            },
            {
                "label": "Detroit Pistons",
                "value": "detroit pistons",
                "abbreviation": "DET",
                "aliases": ["detroit pistons", "pistons", "det"],
            },
            {
                "label": "Golden State Warriors",
                "value": "golden state warriors",
                "abbreviation": "GSW",
                "aliases": ["golden state warriors", "warriors", "gsw"],
            },
            {
                "label": "Houston Rockets",
                "value": "houston rockets",
                "abbreviation": "HOU",
                "aliases": ["houston rockets", "rockets", "hou"],
            },
            {
                "label": "Indiana Pacers",
                "value": "indiana pacers",
                "abbreviation": "IND",
                "aliases": ["indiana pacers", "pacers", "ind"],
            },
            {
                "label": "LA Clippers",
                "value": "los angeles clippers",
                "abbreviation": "LAC",
                "aliases": ["la clippers", "los angeles clippers", "clippers", "lac"],
            },
            {
                "label": "Los Angeles Lakers",
                "value": "los angeles lakers",
                "abbreviation": "LAL",
                "aliases": ["los angeles lakers", "la lakers", "lakers", "lal"],
            },
            {
                "label": "Memphis Grizzlies",
                "value": "memphis grizzlies",
                "abbreviation": "MEM",
                "aliases": ["memphis grizzlies", "grizzlies", "grizz", "mem"],
            },
            {
                "label": "Miami Heat",
                "value": "miami heat",
                "abbreviation": "MIA",
                "aliases": ["miami heat", "heat", "mia"],
            },
            {
                "label": "Milwaukee Bucks",
                "value": "milwaukee bucks",
                "abbreviation": "MIL",
                "aliases": ["milwaukee bucks", "bucks", "mil"],
            },
            {
                "label": "Minnesota Timberwolves",
                "value": "minnesota timberwolves",
                "abbreviation": "MIN",
                "aliases": ["minnesota timberwolves", "timberwolves", "wolves", "min"],
            },
            {
                "label": "New Orleans Pelicans",
                "value": "new orleans pelicans",
                "abbreviation": "NOP",
                "aliases": ["new orleans pelicans", "pelicans", "pels", "nop"],
            },
            {
                "label": "New York Knicks",
                "value": "new york knicks",
                "abbreviation": "NYK",
                "aliases": ["new york knicks", "knicks", "nyk"],
            },
            {
                "label": "Oklahoma City Thunder",
                "value": "oklahoma city thunder",
                "abbreviation": "OKC",
                "aliases": ["oklahoma city thunder", "thunder", "okc"],
            },
            {
                "label": "Orlando Magic",
                "value": "orlando magic",
                "abbreviation": "ORL",
                "aliases": ["orlando magic", "magic", "orl"],
            },
            {
                "label": "Philadelphia 76ers",
                "value": "philadelphia 76ers",
                "abbreviation": "PHI",
                "aliases": ["philadelphia 76ers", "76ers", "sixers", "phi"],
            },
            {
                "label": "Phoenix Suns",
                "value": "phoenix suns",
                "abbreviation": "PHX",
                "aliases": ["phoenix suns", "suns", "phx"],
            },
            {
                "label": "Portland Trail Blazers",
                "value": "portland trail blazers",
                "abbreviation": "POR",
                "aliases": ["portland trail blazers", "trail blazers", "blazers", "por"],
            },
            {
                "label": "Sacramento Kings",
                "value": "sacramento kings",
                "abbreviation": "SAC",
                "aliases": ["sacramento kings", "kings", "sac"],
            },
            {
                "label": "San Antonio Spurs",
                "value": "san antonio spurs",
                "abbreviation": "SAS",
                "aliases": ["san antonio spurs", "spurs", "sas"],
            },
            {
                "label": "Toronto Raptors",
                "value": "toronto raptors",
                "abbreviation": "TOR",
                "aliases": ["toronto raptors", "raptors", "tor"],
            },
            {
                "label": "Utah Jazz",
                "value": "utah jazz",
                "abbreviation": "UTA",
                "aliases": ["utah jazz", "jazz", "uta"],
            },
            {
                "label": "Washington Wizards",
                "value": "washington wizards",
                "abbreviation": "WAS",
                "aliases": ["washington wizards", "wizards", "was"],
            },
        ],
    },
    "nfl": {
        "name": "NFL",
        "teams": [
            {
                "label": "Arizona Cardinals",
                "value": "arizona cardinals",
                "abbreviation": "ARI",
                "aliases": ["arizona cardinals", "cardinals", "cards", "ari"],
            },
            {
                "label": "Atlanta Falcons",
                "value": "atlanta falcons",
                "abbreviation": "ATL",
                "aliases": ["atlanta falcons", "falcons", "atl"],
            },
            {
                "label": "Baltimore Ravens",
                "value": "baltimore ravens",
                "abbreviation": "BAL",
                "aliases": ["baltimore ravens", "ravens", "bal"],
            },
            {
                "label": "Buffalo Bills",
                "value": "buffalo bills",
                "abbreviation": "BUF",
                "aliases": ["buffalo bills", "bills", "buf"],
            },
            {
                "label": "Carolina Panthers",
                "value": "carolina panthers",
                "abbreviation": "CAR",
                "aliases": ["carolina panthers", "panthers", "car"],
            },
            {
                "label": "Chicago Bears",
                "value": "chicago bears",
                "abbreviation": "CHI",
                "aliases": ["chicago bears", "bears", "chi"],
            },
            {
                "label": "Cincinnati Bengals",
                "value": "cincinnati bengals",
                "abbreviation": "CIN",
                "aliases": ["cincinnati bengals", "bengals", "cin"],
            },
            {
                "label": "Cleveland Browns",
                "value": "cleveland browns",
                "abbreviation": "CLE",
                "aliases": ["cleveland browns", "browns", "cle"],
            },
            {
                "label": "Dallas Cowboys",
                "value": "dallas cowboys",
                "abbreviation": "DAL",
                "aliases": ["dallas cowboys", "cowboys", "dal"],
            },
            {
                "label": "Denver Broncos",
                "value": "denver broncos",
                "abbreviation": "DEN",
                "aliases": ["denver broncos", "broncos", "den"],
            },
            {
                "label": "Detroit Lions",
                "value": "detroit lions",
                "abbreviation": "DET",
                "aliases": ["detroit lions", "lions", "det"],
            },
            {
                "label": "Green Bay Packers",
                "value": "green bay packers",
                "abbreviation": "GB",
                "aliases": ["green bay packers", "packers", "gb", "gbp"],
            },
            {
                "label": "Houston Texans",
                "value": "houston texans",
                "abbreviation": "HOU",
                "aliases": ["houston texans", "texans", "hou"],
            },
            {
                "label": "Indianapolis Colts",
                "value": "indianapolis colts",
                "abbreviation": "IND",
                "aliases": ["indianapolis colts", "colts", "ind"],
            },
            {
                "label": "Jacksonville Jaguars",
                "value": "jacksonville jaguars",
                "abbreviation": "JAX",
                "aliases": ["jacksonville jaguars", "jaguars", "jags", "jax"],
            },
            {
                "label": "Kansas City Chiefs",
                "value": "kansas city chiefs",
                "abbreviation": "KC",
                "aliases": ["kansas city chiefs", "chiefs", "kc"],
            },
            {
                "label": "Las Vegas Raiders",
                "value": "las vegas raiders",
                "abbreviation": "LV",
                "aliases": ["las vegas raiders", "raiders", "lv", "oakland raiders"],
            },
            {
                "label": "Los Angeles Chargers",
                "value": "los angeles chargers",
                "abbreviation": "LAC",
                "aliases": ["los angeles chargers", "la chargers", "chargers", "lac"],
            },
            {
                "label": "Los Angeles Rams",
                "value": "los angeles rams",
                "abbreviation": "LAR",
                "aliases": ["los angeles rams", "la rams", "rams", "lar"],
            },
            {
                "label": "Miami Dolphins",
                "value": "miami dolphins",
                "abbreviation": "MIA",
                "aliases": ["miami dolphins", "dolphins", "mia"],
            },
            {
                "label": "Minnesota Vikings",
                "value": "minnesota vikings",
                "abbreviation": "MIN",
                "aliases": ["minnesota vikings", "vikings", "min"],
            },
            {
                "label": "New England Patriots",
                "value": "new england patriots",
                "abbreviation": "NE",
                "aliases": ["new england patriots", "patriots", "pats", "ne"],
            },
            {
                "label": "New Orleans Saints",
                "value": "new orleans saints",
                "abbreviation": "NO",
                "aliases": ["new orleans saints", "saints", "no"],
            },
            {
                "label": "New York Giants",
                "value": "new york giants",
                "abbreviation": "NYG",
                "aliases": ["new york giants", "giants", "nyg"],
            },
            {
                "label": "New York Jets",
                "value": "new york jets",
                "abbreviation": "NYJ",
                "aliases": ["new york jets", "jets", "nyj"],
            },
            {
                "label": "Philadelphia Eagles",
                "value": "philadelphia eagles",
                "abbreviation": "PHI",
                "aliases": ["philadelphia eagles", "eagles", "phi"],
            },
            {
                "label": "Pittsburgh Steelers",
                "value": "pittsburgh steelers",
                "abbreviation": "PIT",
                "aliases": ["pittsburgh steelers", "steelers", "pit"],
            },
            {
                "label": "San Francisco 49ers",
                "value": "san francisco 49ers",
                "abbreviation": "SF",
                "aliases": ["san francisco 49ers", "49ers", "niners", "sf"],
            },
            {
                "label": "Seattle Seahawks",
                "value": "seattle seahawks",
                "abbreviation": "SEA",
                "aliases": ["seattle seahawks", "seahawks", "sea"],
            },
            {
                "label": "Tampa Bay Buccaneers",
                "value": "tampa bay buccaneers",
                "abbreviation": "TB",
                "aliases": ["tampa bay buccaneers", "buccaneers", "bucs", "tb"],
            },
            {
                "label": "Tennessee Titans",
                "value": "tennessee titans",
                "abbreviation": "TEN",
                "aliases": ["tennessee titans", "titans", "ten"],
            },
            {
                "label": "Washington Commanders",
                "value": "washington commanders",
                "abbreviation": "WAS",
                "aliases": ["washington commanders", "commanders", "was", "washington football team"],
            },
        ],
    },
    "mlb": {
        "name": "MLB",
        "teams": [
            {
                "label": "Arizona Diamondbacks",
                "value": "arizona diamondbacks",
                "abbreviation": "ARI",
                "aliases": ["arizona diamondbacks", "diamondbacks", "dbacks", "ari"],
            },
            {
                "label": "Atlanta Braves",
                "value": "atlanta braves",
                "abbreviation": "ATL",
                "aliases": ["atlanta braves", "braves", "atl"],
            },
            {
                "label": "Baltimore Orioles",
                "value": "baltimore orioles",
                "abbreviation": "BAL",
                "aliases": ["baltimore orioles", "orioles", "os", "bal"],
            },
            {
                "label": "Boston Red Sox",
                "value": "boston red sox",
                "abbreviation": "BOS",
                "aliases": ["boston red sox", "red sox", "bos"],
            },
            {
                "label": "Chicago Cubs",
                "value": "chicago cubs",
                "abbreviation": "CHC",
                "aliases": ["chicago cubs", "cubs", "chc"],
            },
            {
                "label": "Chicago White Sox",
                "value": "chicago white sox",
                "abbreviation": "CWS",
                "aliases": ["chicago white sox", "white sox", "cws"],
            },
            {
                "label": "Cincinnati Reds",
                "value": "cincinnati reds",
                "abbreviation": "CIN",
                "aliases": ["cincinnati reds", "reds", "cin"],
            },
            {
                "label": "Cleveland Guardians",
                "value": "cleveland guardians",
                "abbreviation": "CLE",
                "aliases": ["cleveland guardians", "guardians", "cle"],
            },
            {
                "label": "Colorado Rockies",
                "value": "colorado rockies",
                "abbreviation": "COL",
                "aliases": ["colorado rockies", "rockies", "col"],
            },
            {
                "label": "Detroit Tigers",
                "value": "detroit tigers",
                "abbreviation": "DET",
                "aliases": ["detroit tigers", "tigers", "det"],
            },
            {
                "label": "Houston Astros",
                "value": "houston astros",
                "abbreviation": "HOU",
                "aliases": ["houston astros", "astros", "hou"],
            },
            {
                "label": "Kansas City Royals",
                "value": "kansas city royals",
                "abbreviation": "KC",
                "aliases": ["kansas city royals", "royals", "kc"],
            },
            {
                "label": "Los Angeles Angels",
                "value": "los angeles angels",
                "abbreviation": "LAA",
                "aliases": ["los angeles angels", "la angels", "angels", "halos", "laa"],
            },
            {
                "label": "Los Angeles Dodgers",
                "value": "los angeles dodgers",
                "abbreviation": "LAD",
                "aliases": ["los angeles dodgers", "la dodgers", "dodgers", "lad"],
            },
            {
                "label": "Miami Marlins",
                "value": "miami marlins",
                "abbreviation": "MIA",
                "aliases": ["miami marlins", "marlins", "mia"],
            },
            {
                "label": "Milwaukee Brewers",
                "value": "milwaukee brewers",
                "abbreviation": "MIL",
                "aliases": ["milwaukee brewers", "brewers", "brew crew", "mil"],
            },
            {
                "label": "Minnesota Twins",
                "value": "minnesota twins",
                "abbreviation": "MIN",
                "aliases": ["minnesota twins", "twins", "min"],
            },
            {
                "label": "New York Mets",
                "value": "new york mets",
                "abbreviation": "NYM",
                "aliases": ["new york mets", "mets", "nym"],
            },
            {
                "label": "New York Yankees",
                "value": "new york yankees",
                "abbreviation": "NYY",
                "aliases": ["new york yankees", "yankees", "nyy"],
            },
            {
                "label": "Oakland Athletics",
                "value": "oakland athletics",
                "abbreviation": "OAK",
                "aliases": ["oakland athletics", "athletics", "a's", "oak"],
            },
            {
                "label": "Philadelphia Phillies",
                "value": "philadelphia phillies",
                "abbreviation": "PHI",
                "aliases": ["philadelphia phillies", "phillies", "phi"],
            },
            {
                "label": "Pittsburgh Pirates",
                "value": "pittsburgh pirates",
                "abbreviation": "PIT",
                "aliases": ["pittsburgh pirates", "pirates", "pit"],
            },
            {
                "label": "San Diego Padres",
                "value": "san diego padres",
                "abbreviation": "SD",
                "aliases": ["san diego padres", "padres", "sd"],
            },
            {
                "label": "San Francisco Giants",
                "value": "san francisco giants",
                "abbreviation": "SF",
                "aliases": ["san francisco giants", "giants", "sf"],
            },
            {
                "label": "Seattle Mariners",
                "value": "seattle mariners",
                "abbreviation": "SEA",
                "aliases": ["seattle mariners", "mariners", "m's", "sea"],
            },
            {
                "label": "St. Louis Cardinals",
                "value": "st. louis cardinals",
                "abbreviation": "STL",
                "aliases": ["st. louis cardinals", "cardinals", "cards", "stl"],
            },
            {
                "label": "Tampa Bay Rays",
                "value": "tampa bay rays",
                "abbreviation": "TB",
                "aliases": ["tampa bay rays", "rays", "tb"],
            },
            {
                "label": "Texas Rangers",
                "value": "texas rangers",
                "abbreviation": "TEX",
                "aliases": ["texas rangers", "rangers", "tex"],
            },
            {
                "label": "Toronto Blue Jays",
                "value": "toronto blue jays",
                "abbreviation": "TOR",
                "aliases": ["toronto blue jays", "blue jays", "jays", "tor"],
            },
            {
                "label": "Washington Nationals",
                "value": "washington nationals",
                "abbreviation": "WSH",
                "aliases": ["washington nationals", "nationals", "nats", "wsh"],
            },
        ],
    },
    "nhl": {
        "name": "NHL",
        "teams": [
            {
                "label": "Anaheim Ducks",
                "value": "anaheim ducks",
                "abbreviation": "ANA",
                "aliases": ["anaheim ducks", "ducks", "ana"],
            },
            {
                "label": "Arizona Coyotes",
                "value": "arizona coyotes",
                "abbreviation": "ARI",
                "aliases": ["arizona coyotes", "coyotes", "yotes", "ari"],
            },
            {
                "label": "Boston Bruins",
                "value": "boston bruins",
                "abbreviation": "BOS",
                "aliases": ["boston bruins", "bruins", "bos"],
            },
            {
                "label": "Buffalo Sabres",
                "value": "buffalo sabres",
                "abbreviation": "BUF",
                "aliases": ["buffalo sabres", "sabres", "buf"],
            },
            {
                "label": "Calgary Flames",
                "value": "calgary flames",
                "abbreviation": "CGY",
                "aliases": ["calgary flames", "flames", "cgy"],
            },
            {
                "label": "Carolina Hurricanes",
                "value": "carolina hurricanes",
                "abbreviation": "CAR",
                "aliases": ["carolina hurricanes", "hurricanes", "canes", "car"],
            },
            {
                "label": "Chicago Blackhawks",
                "value": "chicago blackhawks",
                "abbreviation": "CHI",
                "aliases": ["chicago blackhawks", "blackhawks", "hawks", "chi"],
            },
            {
                "label": "Colorado Avalanche",
                "value": "colorado avalanche",
                "abbreviation": "COL",
                "aliases": ["colorado avalanche", "avalanche", "avs", "col"],
            },
            {
                "label": "Columbus Blue Jackets",
                "value": "columbus blue jackets",
                "abbreviation": "CBJ",
                "aliases": ["columbus blue jackets", "blue jackets", "cbj"],
            },
            {
                "label": "Dallas Stars",
                "value": "dallas stars",
                "abbreviation": "DAL",
                "aliases": ["dallas stars", "stars", "dal"],
            },
            {
                "label": "Detroit Red Wings",
                "value": "detroit red wings",
                "abbreviation": "DET",
                "aliases": ["detroit red wings", "red wings", "wings", "det"],
            },
            {
                "label": "Edmonton Oilers",
                "value": "edmonton oilers",
                "abbreviation": "EDM",
                "aliases": ["edmonton oilers", "oilers", "edm"],
            },
            {
                "label": "Florida Panthers",
                "value": "florida panthers",
                "abbreviation": "FLA",
                "aliases": ["florida panthers", "panthers", "fla"],
            },
            {
                "label": "Los Angeles Kings",
                "value": "los angeles kings",
                "abbreviation": "LAK",
                "aliases": ["los angeles kings", "la kings", "kings", "lak"],
            },
            {
                "label": "Minnesota Wild",
                "value": "minnesota wild",
                "abbreviation": "MIN",
                "aliases": ["minnesota wild", "wild", "min"],
            },
            {
                "label": "Montreal Canadiens",
                "value": "montreal canadiens",
                "abbreviation": "MTL",
                "aliases": ["montreal canadiens", "canadiens", "habs", "mtl"],
            },
            {
                "label": "Nashville Predators",
                "value": "nashville predators",
                "abbreviation": "NSH",
                "aliases": ["nashville predators", "predators", "preds", "nsh"],
            },
            {
                "label": "New Jersey Devils",
                "value": "new jersey devils",
                "abbreviation": "NJD",
                "aliases": ["new jersey devils", "devils", "njd"],
            },
            {
                "label": "New York Islanders",
                "value": "new york islanders",
                "abbreviation": "NYI",
                "aliases": ["new york islanders", "islanders", "nyi"],
            },
            {
                "label": "New York Rangers",
                "value": "new york rangers",
                "abbreviation": "NYR",
                "aliases": ["new york rangers", "rangers", "nyr"],
            },
            {
                "label": "Ottawa Senators",
                "value": "ottawa senators",
                "abbreviation": "OTT",
                "aliases": ["ottawa senators", "senators", "sens", "ott"],
            },
            {
                "label": "Philadelphia Flyers",
                "value": "philadelphia flyers",
                "abbreviation": "PHI",
                "aliases": ["philadelphia flyers", "flyers", "phi"],
            },
            {
                "label": "Pittsburgh Penguins",
                "value": "pittsburgh penguins",
                "abbreviation": "PIT",
                "aliases": ["pittsburgh penguins", "penguins", "pens", "pit"],
            },
            {
                "label": "San Jose Sharks",
                "value": "san jose sharks",
                "abbreviation": "SJS",
                "aliases": ["san jose sharks", "sharks", "sjs"],
            },
            {
                "label": "Seattle Kraken",
                "value": "seattle kraken",
                "abbreviation": "SEA",
                "aliases": ["seattle kraken", "kraken", "sea"],
            },
            {
                "label": "St. Louis Blues",
                "value": "st. louis blues",
                "abbreviation": "STL",
                "aliases": ["st. louis blues", "blues", "stl"],
            },
            {
                "label": "Tampa Bay Lightning",
                "value": "tampa bay lightning",
                "abbreviation": "TBL",
                "aliases": ["tampa bay lightning", "lightning", "tbl", "bolts"],
            },
            {
                "label": "Toronto Maple Leafs",
                "value": "toronto maple leafs",
                "abbreviation": "TOR",
                "aliases": ["toronto maple leafs", "maple leafs", "leafs", "tor"],
            },
            {
                "label": "Vancouver Canucks",
                "value": "vancouver canucks",
                "abbreviation": "VAN",
                "aliases": ["vancouver canucks", "canucks", "van"],
            },
            {
                "label": "Vegas Golden Knights",
                "value": "vegas golden knights",
                "abbreviation": "VGK",
                "aliases": ["vegas golden knights", "golden knights", "knights", "vgk"],
            },
            {
                "label": "Washington Capitals",
                "value": "washington capitals",
                "abbreviation": "WSH",
                "aliases": ["washington capitals", "capitals", "caps", "wsh"],
            },
            {
                "label": "Winnipeg Jets",
                "value": "winnipeg jets",
                "abbreviation": "WPG",
                "aliases": ["winnipeg jets", "jets", "wpg"],
            },
        ],
    },
}


def list_leagues() -> List[str]:
    """Return the league identifiers in display order."""
    return list(TEAM_CATALOG.keys())


def get_league_catalog(league_id: str) -> Dict[str, object]:
    """Return raw catalog information for a specific league."""
    return TEAM_CATALOG.get(league_id.lower(), {})


def _expand_aliases(primary: str, label: str, abbreviation: str, aliases: List[str]) -> List[str]:
    alias_set = set()
    for value in [primary, label, abbreviation]:
        if value:
            alias_set.add(value.lower())
            alias_set.update(value.lower().replace(".", "").split())
    for alias in aliases or []:
        if alias:
            alias_set.add(alias.lower())
            alias_set.update(alias.lower().replace(".", "").split())
    return sorted(alias_set)


def get_normalized_league(league_id: str) -> Dict[str, object]:
    """Return league data with expanded alias lists for UI and matching."""
    league = get_league_catalog(league_id)
    if not league:
        return {}

    normalized_teams = []
    for team in league["teams"]:
        primary = team["value"]
        label = team["label"]
        abbreviation = team["abbreviation"]
        aliases = _expand_aliases(primary, label, abbreviation, team.get("aliases", []))
        normalized_teams.append(
            {
                "label": label,
                "value": primary,
                "abbreviation": abbreviation,
                "aliases": aliases,
            }
        )

    return {"name": league["name"], "teams": normalized_teams}


def build_alias_lookup(league_id: str) -> Dict[str, str]:
    """Map every alias for a league back to its primary team value."""
    normalized = get_normalized_league(league_id)
    lookup: Dict[str, str] = {}
    if not normalized:
        return lookup

    for team in normalized["teams"]:
        primary = team["value"]
        for alias in team["aliases"]:
            lookup[alias] = primary

        # Include combined forms (e.g., 'losangeleslakers')
        condensed = primary.replace(" ", "")
        lookup.setdefault(condensed, primary)
    return lookup
