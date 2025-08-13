import requests
import csv
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Create directories if they don't exist
sprites_dir = Path("sprites")
sprites_dir.mkdir(exist_ok=True)

# Create a cache directory
cache_dir = Path("cache")
cache_dir.mkdir(exist_ok=True)
pokemon_details_dir = cache_dir / "pokemon_details"
pokemon_details_dir.mkdir(exist_ok=True)
evolution_chains_dir = cache_dir / "evolution_chains"
evolution_chains_dir.mkdir(exist_ok=True)

# Cache files
POKEMON_CACHE_FILE = cache_dir / "pokemon_list.json"
EVOLUTION_CHAINS_CACHE_FILE = cache_dir / "evolution_chains_list.json"

# Cache will always be used unless force_refresh is specified

# Base URL for the PokeAPI
BASE_URL = "https://pokeapi.co/api/v2/"

def is_cache_valid():
    """Check if the cache file exists"""
    return POKEMON_CACHE_FILE.exists()

def save_pokemon_cache(pokemon_list):
    """Save the Pokemon list to cache"""
    try:
        with open(POKEMON_CACHE_FILE, 'w') as f:
            # Save the list along with a timestamp
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'pokemon_list': pokemon_list
            }
            json.dump(cache_data, f, indent=2)
        print(f"Pokemon list cached to {POKEMON_CACHE_FILE}")
        return True
    except Exception as e:
        print(f"Error saving Pokemon cache: {e}")
        return False

def load_pokemon_cache():
    """Load the Pokemon list from cache"""
    try:
        with open(POKEMON_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            print(f"Loaded Pokemon list from cache (created on {cache_data['timestamp']})")
            return cache_data['pokemon_list']
    except Exception as e:
        print(f"Error loading Pokemon cache: {e}")
        return None

def fetch_pokemon_from_api():
    """Fetch a list of all Pokemon from the API using pagination"""
    url = f"{BASE_URL}pokemon"
    all_pokemon = []
    
    while url:
        print(f"Fetching: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            all_pokemon.extend(data["results"])
            url = data["next"]  # Get the URL for the next page
            
            # Be nice to the API - add a small delay between requests
            time.sleep(0.1)
        else:
            print(f"Failed to fetch Pokemon list: {response.status_code}")
            break
    
    # Save the fetched list to cache
    if all_pokemon:
        save_pokemon_cache(all_pokemon)
    
    return all_pokemon

def get_all_pokemon():
    """Get a list of all Pokemon, using cache if available and valid"""
    if is_cache_valid():
        cached_pokemon = load_pokemon_cache()
        if cached_pokemon:
            return cached_pokemon
    
    # If cache is invalid or loading failed, fetch from API
    print("Cache not available or invalid. Fetching from API...")
    return fetch_pokemon_from_api()

def get_pokemon_details(pokemon_url):
    """Fetch details for a specific Pokemon, using cache if available"""
    # Extract pokemon name from URL to use as cache key
    pokemon_name = pokemon_url.rstrip('/').split('/')[-1]
    cache_file = pokemon_details_dir / f"{pokemon_name}.json"
    
    # Check if we have a cache for this Pokemon
    if cache_file.exists():
        try:
            # Cache exists, load it
            with open(cache_file, 'r') as f:
                return json.load(f), True  # Return data and cache_hit=True
        except Exception as e:
            print(f"Error reading cache for {pokemon_name}: {e}")
    
    # If we get here, we need to fetch from the API
    print(f"Fetching details for {pokemon_name} from API")
    response = requests.get(pokemon_url)
    
    if response.status_code == 200:
        pokemon_data = response.json()
        
        # Save to cache
        try:
            with open(cache_file, 'w') as f:
                json.dump(pokemon_data, f)
        except Exception as e:
            print(f"Error saving cache for {pokemon_name}: {e}")
        
        return pokemon_data, False  # Return data and cache_hit=False
    else:
        print(f"Failed to fetch Pokemon details: {response.status_code}")
        return None, False

def get_stat(pokemon_data, stat_name):
    """Extract a specific stat from Pokemon data"""
    for stat in pokemon_data["stats"]:
        if stat["stat"]["name"] == stat_name:
            return stat["base_stat"]
    return None

def get_types(pokemon_data):
    """Extract types from Pokemon data"""
    return [t["type"]["name"] for t in pokemon_data["types"]]

def download_sprite(sprite_url, pokemon_name):
    """Download and save a sprite image, using cached version if available"""
    # Create a file path for the sprite
    file_path = sprites_dir / f"{pokemon_name}.png"
    
    # Check if the sprite already exists
    if file_path.exists():
        print(f"Using cached sprite for {pokemon_name}")
        return file_path
    
    # If not, download it
    print(f"Downloading sprite for {pokemon_name}")
    response = requests.get(sprite_url)
    if response.status_code == 200:
        # Save the image
        with open(file_path, "wb") as f:
            f.write(response.content)
        
        return file_path
    else:
        print(f"Failed to download sprite for {pokemon_name}: {response.status_code}")
        return None

def get_pokemon_details_with_retry(pokemon_url, max_retries=3, force_refresh=False):
    """Get Pokemon details with retry logic"""
    retries = 0
    while retries < max_retries:
        try:
            # If force_refresh is True, we'll skip the cache check in get_pokemon_details
            if force_refresh:
                # Extract pokemon name from URL to use as cache key
                pokemon_name = pokemon_url.rstrip('/').split('/')[-1]
                cache_file = pokemon_details_dir / f"{pokemon_name}.json"
                
                # If the cache file exists and we're forcing a refresh, remove it
                if cache_file.exists():
                    cache_file.unlink()
                    print(f"Removed cache for {pokemon_name} to force refresh")
            
            data, from_cache = get_pokemon_details(pokemon_url)
            return data, from_cache
        except Exception as e:
            retries += 1
            print(f"Error fetching Pokemon details (attempt {retries}/{max_retries}): {e}")
            if retries < max_retries:
                # Exponential backoff
                wait_time = 2 ** retries
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    print(f"Failed to fetch Pokemon details after {max_retries} attempts")
    return None, False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Fetch Pokemon data and save to CSV')
    parser.add_argument('--force-refresh', action='store_true', 
                        help='Force refresh of cached data')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit the number of Pokemon to process (for testing)')
    parser.add_argument('--output', type=str, default="pokemon_data.csv",
                        help='Output CSV file name')
    
    # Field selection options
    field_group = parser.add_mutually_exclusive_group()
    field_group.add_argument('--fields', type=str,
                        help='Comma-separated list of fields to fetch. Available fields: name, id, height, weight, '
                             'speed, attack, defense, hp, special-attack, special-defense, sprite, types')
    field_group.add_argument('--all-stats', action='store_true',
                        help='Include all stats (hp, attack, defense, special-attack, special-defense, speed)')
    field_group.add_argument('--all-fields', action='store_true', default=True,
                        help='Include all available fields (default)')
    
    # Image handling options
    parser.add_argument('--download-images', action='store_true', dest='download_images',
                        help='Download sprite images')
    parser.add_argument('--no-download-images', action='store_false', dest='download_images', default=False,
                        help='Do not download sprite images, just save URLs (default)')
    
    # Evolution data options
    parser.add_argument('--evolution-data', action='store_true',
                        help='Collect evolution chain data for AI analysis')
    parser.add_argument('--evolution-output', type=str, default="evolution_data.csv",
                        help='Output CSV file for evolution data')
    parser.add_argument('--evolution-limit', type=int, default=None,
                        help='Limit the number of evolution chains to process')
    
    return parser.parse_args()

def get_field_value(pokemon_data, field, pokemon_name, download_images=True):
    """Get the value for a specific field from Pokemon data"""
    if field == "name":
        return pokemon_name
    elif field == "id":
        return pokemon_data.get("id")
    elif field == "height":
        return pokemon_data.get("height")
    elif field == "weight":
        return pokemon_data.get("weight")
    elif field == "speed":
        return get_stat(pokemon_data, "speed")
    elif field == "attack":
        return get_stat(pokemon_data, "attack")
    elif field == "defense":
        return get_stat(pokemon_data, "defense")
    elif field == "hp":
        return get_stat(pokemon_data, "hp")
    elif field == "special-attack":
        return get_stat(pokemon_data, "special-attack")
    elif field == "special-defense":
        return get_stat(pokemon_data, "special-defense")
    elif field == "sprite":
        sprite_url = pokemon_data["sprites"]["front_default"]
        if not sprite_url:
            return None
        
        if download_images:
            # Download and return local path
            sprite_path = download_sprite(sprite_url, pokemon_name)
            return str(sprite_path) if sprite_path else None
        else:
            # Just return the URL
            return sprite_url
    elif field == "types":
        return ", ".join(get_types(pokemon_data))
    else:
        return None

def main():
    # Parse command line arguments
    args = parse_arguments()
    force_refresh = args.force_refresh
    limit = args.limit
    output_file = args.output
    download_images = args.download_images
    
    # Define all available fields
    all_available_fields = ["name", "id", "height", "weight", "hp", "attack", "defense", 
                           "special-attack", "special-defense", "speed", "types", "sprite"]
    all_stats_fields = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
    
    # Parse fields to fetch based on command-line options
    if args.all_fields or not args.fields:
        fields = all_available_fields
    elif args.all_stats:
        fields = ["name", "id"] + all_stats_fields + ["sprite"]
    else:
        fields = [f.strip() for f in args.fields.split(",")]
    
    print(f"Starting Pokemon data fetcher")
    print(f"Force refresh: {force_refresh}")
    print(f"Fields to fetch: {', '.join(fields)}")
    print(f"Download images: {download_images}")
    if limit:
        print(f"Processing limit: {limit} Pokemon")
    
    try:
        # Create or open the CSV file
        with open(output_file, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write the header
            csv_writer.writerow(fields)
            
            # Get all Pokemon
            print("Fetching complete Pokemon list (this may take a while)...")
            pokemon_list = get_all_pokemon()
            
            # Apply limit if specified
            if limit and limit > 0:
                pokemon_list = pokemon_list[:limit]
                print(f"Limited to first {limit} Pokemon")
            
            total_pokemon = len(pokemon_list)
            print(f"Found {total_pokemon} Pokemon to process")
            
            # Process each Pokemon
            processed = 0
            skipped = 0
            start_time = time.time()
            
            for i, pokemon in enumerate(pokemon_list):
                pokemon_name = pokemon["name"]
                
                # Print progress every 10 Pokemon or for the first few
                if i < 5 or i % 10 == 0:
                    elapsed = time.time() - start_time
                    if i > 0:
                        avg_time_per_pokemon = elapsed / i
                        est_remaining = avg_time_per_pokemon * (total_pokemon - i)
                        est_remaining_str = f", Est. remaining: {est_remaining:.1f}s"
                    else:
                        est_remaining_str = ""
                    
                    print(f"Processing {i+1}/{total_pokemon}: {pokemon_name} "
                          f"(Processed: {processed}, Skipped: {skipped}{est_remaining_str})")
                
                try:
                    # Get Pokemon details
                    pokemon_data, from_cache = get_pokemon_details_with_retry(pokemon["url"], force_refresh=force_refresh)
                    if not pokemon_data:
                        skipped += 1
                        continue
                    
                    # Get values for each requested field
                    row_data = []
                    skip_pokemon = False
                    
                    for field in fields:
                        value = get_field_value(pokemon_data, field, pokemon_name, download_images)
                        if value is None and field != "name":  # Name should always be available
                            print(f"No {field} data found for {pokemon_name}")
                            skip_pokemon = True
                            break
                        row_data.append(value)
                    
                    if skip_pokemon:
                        skipped += 1
                        continue
                    
                    # Write to CSV
                    csv_writer.writerow(row_data)
                    processed += 1
                    
                except Exception as e:
                    print(f"Error processing {pokemon_name}: {e}")
                    skipped += 1
                    continue
                
                # Be nice to the API - add a small delay between requests, but only if we actually used the API
                if not from_cache:
                    time.sleep(0.1)
            
            total_time = time.time() - start_time
            print(f"\nDone! Processed {processed} Pokemon, skipped {skipped}.")
            print(f"Total time: {total_time:.1f} seconds")
            print(f"Data saved to {output_file}")
            if download_images and any(field == "sprite" for field in fields):
                print(f"Sprite images saved to {sprites_dir}/")
            
            # Print a sample of the data
            try:
                with open(output_file, "r") as f:
                    sample = [next(f) for _ in range(min(6, processed + 1))]
                    print("\nSample of the CSV data:")
                    for line in sample:
                        print(line.strip())
            except Exception as e:
                print(f"Could not read sample data: {e}")
    
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nError in main process: {e}")
        import traceback
        traceback.print_exc()


def fetch_evolution_chains(force_refresh=False, limit=None):
    """Fetch all evolution chains from the API"""
    # Check if we have a cache of evolution chains
    if EVOLUTION_CHAINS_CACHE_FILE.exists() and not force_refresh:
        try:
            with open(EVOLUTION_CHAINS_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                print(f"Loaded evolution chains from cache (created on {cache_data['timestamp']})")
                return cache_data['evolution_chains']
        except Exception as e:
            print(f"Error loading evolution chains cache: {e}")
    
    # If we get here, we need to fetch from the API
    print("Fetching evolution chains from API...")
    url = f"{BASE_URL}evolution-chain"
    all_chains = []
    
    while url:
        print(f"Fetching: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            all_chains.extend(data["results"])
            url = data.get("next")  # Get the URL for the next page
            
            # Apply limit if specified
            if limit and len(all_chains) >= limit:
                all_chains = all_chains[:limit]
                break
            
            # Be nice to the API - add a small delay between requests
            time.sleep(0.1)
        else:
            print(f"Failed to fetch evolution chains: {response.status_code}")
            break
    
    # Save the fetched list to cache
    if all_chains:
        try:
            with open(EVOLUTION_CHAINS_CACHE_FILE, 'w') as f:
                # Save the list along with a timestamp
                cache_data = {
                    'timestamp': datetime.now().isoformat(),
                    'evolution_chains': all_chains
                }
                json.dump(cache_data, f, indent=2)
            print(f"Evolution chains cached to {EVOLUTION_CHAINS_CACHE_FILE}")
        except Exception as e:
            print(f"Error saving evolution chains cache: {e}")
    
    return all_chains

def get_evolution_chain_details(chain_url, force_refresh=False):
    """Fetch details for a specific evolution chain, using cache if available"""
    # Extract chain ID from URL to use as cache key
    chain_id = chain_url.rstrip('/').split('/')[-1]
    cache_file = evolution_chains_dir / f"chain_{chain_id}.json"
    
    # Check if we have a cache for this chain
    if cache_file.exists() and not force_refresh:
        try:
            # Cache exists, load it
            with open(cache_file, 'r') as f:
                return json.load(f), True  # Return data and cache_hit=True
        except Exception as e:
            print(f"Error reading cache for evolution chain {chain_id}: {e}")
    
    # If we get here, we need to fetch from the API
    print(f"Fetching details for evolution chain {chain_id} from API")
    response = requests.get(chain_url)
    
    if response.status_code == 200:
        chain_data = response.json()
        
        # Save to cache
        try:
            with open(cache_file, 'w') as f:
                json.dump(chain_data, f)
        except Exception as e:
            print(f"Error saving cache for evolution chain {chain_id}: {e}")
        
        return chain_data, False  # Return data and cache_hit=False
    else:
        print(f"Failed to fetch evolution chain details: {response.status_code}")
        return None, False

def extract_evolution_pairs(chain_data):
    """Extract all evolution pairs from an evolution chain"""
    pairs = []
    
    def process_chain_link(chain_link, parent=None):
        current_species = chain_link["species"]
        
        # If we have a parent, this is an evolution pair
        if parent:
            pairs.append({
                "pre_evolution": parent,
                "evolution": current_species
            })
        
        # Process any further evolutions
        for evolves_to in chain_link.get("evolves_to", []):
            process_chain_link(evolves_to, current_species)
    
    # Start with the base chain link
    if chain_data and "chain" in chain_data:
        process_chain_link(chain_data["chain"])
    
    return pairs

def get_pokemon_stats(pokemon_data):
    """Extract all stats from Pokemon data"""
    stats = {}
    for stat in pokemon_data.get("stats", []):
        stat_name = stat["stat"]["name"]
        stat_value = stat["base_stat"]
        stats[stat_name] = stat_value
    return stats

def collect_evolution_data(force_refresh=False, limit=None, download_images=True, output_file="evolution_data.csv", fields=None):
    """Collect data for all evolution pairs and save to CSV"""
    print("Starting evolution data collection...")
    
    # Get all evolution chains
    chains = fetch_evolution_chains(force_refresh, limit)
    print(f"Found {len(chains)} evolution chains")
    
    # Define all available fields if not provided
    if not fields:
        fields = ["name", "id", "height", "weight", "hp", "attack", "defense", 
                 "special-attack", "special-defense", "speed", "types", "sprite"]
    
    # Prepare CSV file fieldnames based on selected fields
    fieldnames = []
    
    # Add pre-evolution fields
    for field in fields:
        fieldnames.append(f"pre_evolution_{field}")
    
    # Add evolution fields
    for field in fields:
        fieldnames.append(f"evolution_{field}")
    
    # Add stat change fields if the corresponding stats are included
    stat_fields = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
    for stat in stat_fields:
        if stat in fields:
            fieldnames.append(f"{stat}_change")
    
    with open(output_file, "w", newline="") as csvfile:
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        processed_chains = 0
        processed_pairs = 0
        skipped_pairs = 0
        
        for chain_info in chains:
            try:
                # Get chain details
                chain_data, from_cache = get_evolution_chain_details(chain_info["url"], force_refresh)
                if not chain_data:
                    continue
                
                # Extract evolution pairs
                pairs = extract_evolution_pairs(chain_data)
                
                for pair in pairs:
                    try:
                        # Get pre-evolution details
                        pre_evo_data, pre_from_cache = get_pokemon_details_with_retry(
                            f"{BASE_URL}pokemon/{pair['pre_evolution']['name']}", force_refresh=force_refresh)
                        
                        # Get evolution details
                        evo_data, evo_from_cache = get_pokemon_details_with_retry(
                            f"{BASE_URL}pokemon/{pair['evolution']['name']}", force_refresh=force_refresh)
                        
                        if not pre_evo_data or not evo_data:
                            skipped_pairs += 1
                            continue
                        
                        # Prepare row data
                        row_data = {}
                        
                        # Process each field for pre-evolution
                        for field in fields:
                            if field == "name":
                                row_data[f"pre_evolution_{field}"] = pair['pre_evolution']['name']
                            elif field == "id":
                                row_data[f"pre_evolution_{field}"] = pre_evo_data.get("id")
                            elif field == "height":
                                row_data[f"pre_evolution_{field}"] = pre_evo_data.get("height")
                            elif field == "weight":
                                row_data[f"pre_evolution_{field}"] = pre_evo_data.get("weight")
                            elif field in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]:
                                row_data[f"pre_evolution_{field}"] = get_stat(pre_evo_data, field)
                            elif field == "types":
                                row_data[f"pre_evolution_{field}"] = ", ".join(get_types(pre_evo_data))
                            elif field == "sprite":
                                sprite_url = pre_evo_data["sprites"]["front_default"]
                                if not sprite_url:
                                    row_data[f"pre_evolution_{field}"] = None
                                elif download_images:
                                    sprite_path = download_sprite(sprite_url, pair['pre_evolution']['name'])
                                    row_data[f"pre_evolution_{field}"] = str(sprite_path) if sprite_path else None
                                else:
                                    row_data[f"pre_evolution_{field}"] = sprite_url
                        
                        # Process each field for evolution
                        for field in fields:
                            if field == "name":
                                row_data[f"evolution_{field}"] = pair['evolution']['name']
                            elif field == "id":
                                row_data[f"evolution_{field}"] = evo_data.get("id")
                            elif field == "height":
                                row_data[f"evolution_{field}"] = evo_data.get("height")
                            elif field == "weight":
                                row_data[f"evolution_{field}"] = evo_data.get("weight")
                            elif field in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]:
                                row_data[f"evolution_{field}"] = get_stat(evo_data, field)
                            elif field == "types":
                                row_data[f"evolution_{field}"] = ", ".join(get_types(evo_data))
                            elif field == "sprite":
                                sprite_url = evo_data["sprites"]["front_default"]
                                if not sprite_url:
                                    row_data[f"evolution_{field}"] = None
                                elif download_images:
                                    sprite_path = download_sprite(sprite_url, pair['evolution']['name'])
                                    row_data[f"evolution_{field}"] = str(sprite_path) if sprite_path else None
                                else:
                                    row_data[f"evolution_{field}"] = sprite_url
                        
                        # Calculate stat changes for included stats
                        stat_fields = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
                        for stat in stat_fields:
                            if stat in fields:
                                pre_value = get_stat(pre_evo_data, stat) or 0
                                evo_value = get_stat(evo_data, stat) or 0
                                row_data[f"{stat}_change"] = evo_value - pre_value
                        
                        # Write to CSV
                        csv_writer.writerow(row_data)
                        processed_pairs += 1
                        
                        # Be nice to the API - add a small delay between requests, but only if we actually used the API
                        if not pre_from_cache or not evo_from_cache:
                            time.sleep(0.1)
                            
                    except Exception as e:
                        print(f"Error processing evolution pair {pair['pre_evolution']['name']} -> {pair['evolution']['name']}: {e}")
                        skipped_pairs += 1
                        continue
                
                processed_chains += 1
                
                # Print progress every 5 chains
                if processed_chains % 5 == 0 or processed_chains == 1:
                    print(f"Processed {processed_chains}/{len(chains)} chains, {processed_pairs} pairs, {skipped_pairs} skipped")
                    
            except Exception as e:
                print(f"Error processing evolution chain {chain_info['url']}: {e}")
                continue
    
    print(f"\nDone! Processed {processed_chains} evolution chains with {processed_pairs} evolution pairs.")
    print(f"Skipped {skipped_pairs} pairs due to errors or missing data.")
    print(f"Evolution data saved to {output_file}")
    
    # Print a sample of the data
    try:
        with open(output_file, "r") as f:
            sample = [next(f) for _ in range(min(6, processed_pairs + 1))]
            print("\nSample of the CSV data:")
            for line in sample:
                print(line.strip())
    except Exception as e:
        print(f"Could not read sample data: {e}")

def main():
    # Parse command line arguments
    args = parse_arguments()
    force_refresh = args.force_refresh
    limit = args.limit
    output_file = args.output
    download_images = args.download_images
    
    # Define all available fields
    all_available_fields = ["name", "id", "height", "weight", "hp", "attack", "defense", 
                           "special-attack", "special-defense", "speed", "types", "sprite"]
    all_stats_fields = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
    
    # Parse fields to fetch based on command-line options
    if args.all_fields or not args.fields:
        fields = all_available_fields
    elif args.all_stats:
        fields = ["name", "id"] + all_stats_fields + ["sprite"]
    else:
        fields = [f.strip() for f in args.fields.split(",")]
    
    # Check if we should collect evolution data
    if args.evolution_data:
        collect_evolution_data(
            force_refresh=force_refresh,
            limit=args.evolution_limit,
            download_images=download_images,
            output_file=args.evolution_output,
            fields=fields  # Pass the fields parameter to collect_evolution_data
        )
        return
    
    print(f"Starting Pokemon data fetcher")
    print(f"Force refresh: {force_refresh}")
    print(f"Fields to fetch: {', '.join(fields)}")
    print(f"Download images: {download_images}")
    if limit:
        print(f"Processing limit: {limit} Pokemon")
    
    try:
        # Create or open the CSV file
        with open(output_file, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write the header
            csv_writer.writerow(fields)
            
            # Get all Pokemon
            print("Fetching complete Pokemon list (this may take a while)...")
            pokemon_list = get_all_pokemon()
            
            # Apply limit if specified
            if limit and limit > 0:
                pokemon_list = pokemon_list[:limit]
                print(f"Limited to first {limit} Pokemon")
            
            total_pokemon = len(pokemon_list)
            print(f"Found {total_pokemon} Pokemon to process")
            
            # Process each Pokemon
            processed = 0
            skipped = 0
            start_time = time.time()
            
            for i, pokemon in enumerate(pokemon_list):
                pokemon_name = pokemon["name"]
                
                # Print progress every 10 Pokemon or for the first few
                if i < 5 or i % 10 == 0:
                    elapsed = time.time() - start_time
                    if i > 0:
                        avg_time_per_pokemon = elapsed / i
                        est_remaining = avg_time_per_pokemon * (total_pokemon - i)
                        est_remaining_str = f", Est. remaining: {est_remaining:.1f}s"
                    else:
                        est_remaining_str = ""
                    
                    print(f"Processing {i+1}/{total_pokemon}: {pokemon_name} "
                          f"(Processed: {processed}, Skipped: {skipped}{est_remaining_str})")
                
                try:
                    # Get Pokemon details
                    pokemon_data, from_cache = get_pokemon_details_with_retry(pokemon["url"], force_refresh=force_refresh)
                    if not pokemon_data:
                        skipped += 1
                        continue
                    
                    # Get values for each requested field
                    row_data = []
                    skip_pokemon = False
                    
                    for field in fields:
                        value = get_field_value(pokemon_data, field, pokemon_name, download_images)
                        if value is None and field != "name":  # Name should always be available
                            print(f"No {field} data found for {pokemon_name}")
                            skip_pokemon = True
                            break
                        row_data.append(value)
                    
                    if skip_pokemon:
                        skipped += 1
                        continue
                    
                    # Write to CSV
                    csv_writer.writerow(row_data)
                    processed += 1
                    
                except Exception as e:
                    print(f"Error processing {pokemon_name}: {e}")
                    skipped += 1
                    continue
                
                # Be nice to the API - add a small delay between requests, but only if we actually used the API
                if not from_cache:
                    time.sleep(0.1)
            
            total_time = time.time() - start_time
            print(f"\nDone! Processed {processed} Pokemon, skipped {skipped}.")
            print(f"Total time: {total_time:.1f} seconds")
            print(f"Data saved to {output_file}")
            if download_images and any(field == "sprite" for field in fields):
                print(f"Sprite images saved to {sprites_dir}/")
            
            # Print a sample of the data
            try:
                with open(output_file, "r") as f:
                    sample = [next(f) for _ in range(min(6, processed + 1))]
                    print("\nSample of the CSV data:")
                    for line in sample:
                        print(line.strip())
            except Exception as e:
                print(f"Could not read sample data: {e}")
    
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nError in main process: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
