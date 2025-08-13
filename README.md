# Pokémon API Fetcher

A Python utility for fetching Pokémon data from the [PokeAPI](https://pokeapi.co/) and saving it to CSV format.

## Features

- Fetch data for all Pokémon or limit to a specific number
- Select which fields to fetch (name, stats, types, sprites, etc.)
- Download sprite images or just save URLs
- Efficient caching system to minimize API calls
- Progress reporting with estimated time remaining

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/poke_api_fetcher.git
   cd poke_api_fetcher
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Basic usage:
```
python poke_api_fetcher.py
```

This will fetch the name, speed stat, and front_default sprite for all Pokémon, download the sprite images, and save the data to a CSV file.

### Command-line Options

| Option | Description |
|--------|-------------|
| `--force-refresh` | Force refresh of cached data (Pokémon list, details, sprites) |
| `--limit N` | Limit the number of Pokémon to process (useful for testing) |
| `--output FILENAME` | Specify a custom output CSV filename (default: pokemon_data.csv) |
| `--fields FIELDS` | Comma-separated list of fields to fetch (see available fields below) |
| `--all-stats` | Include all stats (hp, attack, defense, special-attack, special-defense, speed) |
| `--all-fields` | Include all available fields |
| `--download-images` | Download sprite images (default behavior) |
| `--no-download-images` | Do not download sprite images, just save URLs |

### Available Fields

- `name`: Pokémon name
- `id`: Pokémon ID number
- `height`: Pokémon height
- `weight`: Pokémon weight
- `hp`: HP stat
- `attack`: Attack stat
- `defense`: Defense stat
- `special-attack`: Special Attack stat
- `special-defense`: Special Defense stat
- `speed`: Speed stat
- `types`: Pokémon types (comma-separated)
- `sprite`: Front default sprite (URL or local path)

## Examples

Fetch only the first 10 Pokémon:
```
python poke_api_fetcher.py --limit 10
```

Fetch specific fields:
```
python poke_api_fetcher.py --fields "name,id,height,weight,types"
```

Fetch all stats:
```
python poke_api_fetcher.py --all-stats
```

Fetch all available fields:
```
python poke_api_fetcher.py --all-fields
```

Save sprite URLs without downloading images:
```
python poke_api_fetcher.py --no-download-images
```

Force refresh of cached data:
```
python poke_api_fetcher.py --force-refresh
```

Custom output filename:
```
python poke_api_fetcher.py --output my_pokemon_data.csv
```

## Caching

The script uses a caching system to minimize API calls:

- Pokémon list is cached in `cache/pokemon_list.json`
- Individual Pokémon details are cached in `cache/pokemon_details/[pokemon_name].json`
- Sprite images are cached in the `sprites/` directory

By default, the script will use cached data if available. Use the `--force-refresh` option to ignore the cache and fetch fresh data.

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- Data provided by [PokeAPI](https://pokeapi.co/)
