import pandas as pd
import re
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- Configuration ---
COLES_FILE = 'coles_baby.csv'
WW_FILE = 'woolworths_baby.csv'
OUTPUT_FILE = 'matched_products_final.csv'
MEMORY_FILE = 'known_matches.csv'

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    return re.sub(r'[^a-z0-9 ]', '', text)

def clean_price(price_str):
    if pd.isna(price_str):
        return 0.0
    match = re.search(r'^\$?(\d+\.\d{2})', str(price_str))
    return float(match.group(1)) if match else 0.0

def main():
    print("Loading data...")
    coles_df = pd.read_csv(COLES_FILE)
    ww_df = pd.read_csv(WW_FILE)

    # Clean prices and text
    coles_df['clean_price'] = coles_df['price'].apply(clean_price)
    ww_df['clean_price'] = ww_df['price'].apply(clean_price)
    
    coles_df['clean_name'] = coles_df['name'].apply(clean_text)
    ww_df['clean_name'] = ww_df['name'].apply(clean_text)

    # --- Load Memory (Known Matches) ---
    known_matches = {}
    if os.path.exists(MEMORY_FILE):
        mem_df = pd.read_csv(MEMORY_FILE)
        for _, row in mem_df.iterrows():
            known_matches[(row['Coles_Name'], row['WW_Name'])] = row['Is_Match']

    # --- TF-IDF & Similarity ---
    print("Calculating similarities...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    corpus = pd.concat([coles_df['clean_name'], ww_df['clean_name']])
    vectorizer.fit(corpus)

    coles_vecs = vectorizer.transform(coles_df['clean_name'])
    ww_vecs = vectorizer.transform(ww_df['clean_name'])
    sim_matrix = cosine_similarity(coles_vecs, ww_vecs)

    final_matches = []
    new_memory_entries = []
    
    matched_coles_indices = set()
    matched_ww_indices = set()
    items_to_review = []

    # --- PHASE 1: Categorize all items ---
    for i in range(len(coles_df)):
        best_idx = sim_matrix[i].argmax()
        best_score = sim_matrix[i][best_idx]
        
        coles_name = coles_df.iloc[i]['name']
        ww_name = ww_df.iloc[best_idx]['name']
        coles_price = coles_df.iloc[i]['clean_price']
        ww_price = ww_df.iloc[best_idx]['clean_price']
        
        match_data = {
            'Product Name': ww_name, 
            'Woolworths_Price': ww_price,
            'Coles_Price': coles_price,
            'Woolworths_Image': ww_df.iloc[best_idx]['image'],
            'Coles_image': coles_df.iloc[i]['image']
        }

        # 1. Check Memory First
        if (coles_name, ww_name) in known_matches:
            if known_matches[(coles_name, ww_name)] == True:
                final_matches.append(match_data)
                matched_coles_indices.add(i)
                matched_ww_indices.add(best_idx)
                
        # 2. Auto-Approve High Confidence
        elif best_score > 0.95:
            final_matches.append(match_data)
            matched_coles_indices.add(i)
            matched_ww_indices.add(best_idx)
            
        # 3. Queue for confirmation on ambiguous matches
        elif best_score >= 0.55:
            items_to_review.append({
                'coles_idx': i,
                'ww_idx': best_idx,
                'score': best_score,
                'coles_name': coles_name,
                'ww_name': ww_name,
                'coles_price': coles_price,
                'ww_price': ww_price,
                'match_data': match_data
            })

    # --- PHASE 2: Sort and Review ---
    items_to_review.sort(key=lambda x: x['score'], reverse=True)
    total_reviews = len(items_to_review)

    print(f"\n--- Reviewing Matches ({total_reviews} new items need confirmation) ---")
    
    for current_review, item in enumerate(items_to_review, start=1):
        print("\n" + "=" * 60)
        print(f"Reviewing {current_review} of {total_reviews}")
        print(f"Match Similarity: {item['score'] * 100:.1f}%")
        print("-" * 60)
        print(f"Coles:      {item['coles_name']}")
        print(f"Price:      ${item['coles_price']:.2f}")
        print("-" * 60)
        print(f"Woolworths: {item['ww_name']}")
        print(f"Price:      ${item['ww_price']:.2f}")
        print("=" * 60)
        
        while True:
            choice = input("Is this a match? (y/n or 'q' to quit): ").strip().lower()
            if choice in ['y', 'n', 'q']:
                break
            print("Please enter 'y', 'n', or 'q'.")
            
        if choice == 'q':
            print(f"\nSaving your progress ({current_review - 1} items reviewed). You can resume later!")
            break
            
        is_match = (choice == 'y')
        
        # Record choice in memory
        new_memory_entries.append({
            'Coles_Name': item['coles_name'], 
            'WW_Name': item['ww_name'], 
            'Is_Match': is_match
        })

        if is_match:
            final_matches.append(item['match_data'])
            matched_coles_indices.add(item['coles_idx'])
            matched_ww_indices.add(item['ww_idx'])

    # --- PHASE 3: ADD UNMATCHED PRODUCTS ---
    for i in range(len(coles_df)):
        if i not in matched_coles_indices:
            final_matches.append({
                'Product Name': coles_df.iloc[i]['name'], 
                'Woolworths_Price': None,
                'Coles_Price': coles_df.iloc[i]['clean_price'],
                'Woolworths_Image': None,
                'Coles_image': coles_df.iloc[i]['image']
            })
            
    for j in range(len(ww_df)):
        if j not in matched_ww_indices:
            final_matches.append({
                'Product Name': ww_df.iloc[j]['name'], 
                'Woolworths_Price': ww_df.iloc[j]['clean_price'],
                'Coles_Price': None,
                'Woolworths_Image': ww_df.iloc[j]['image'],
                'Coles_image': None
            })

    # --- Save Outputs ---
    if final_matches:
        output_df = pd.DataFrame(final_matches)
        
        # --- REMOVE DUPLICATES ---
        initial_count = len(output_df)
        output_df = output_df.drop_duplicates(subset=['Product Name'], keep='first')
        final_count = len(output_df)
        duplicates_removed = initial_count - final_count
        
        output_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved {final_count} total items to {OUTPUT_FILE}")
        if duplicates_removed > 0:
            print(f"Cleaned up list: Removed {duplicates_removed} duplicate product names.")
    else:
        print("\nNo items to save.")

    # Append to memory file
    if new_memory_entries:
        new_mem_df = pd.DataFrame(new_memory_entries)
        if os.path.exists(MEMORY_FILE):
            existing_mem = pd.read_csv(MEMORY_FILE)
            new_mem_df = pd.concat([existing_mem, new_mem_df], ignore_index=True)
            new_mem_df = new_mem_df.drop_duplicates(subset=['Coles_Name', 'WW_Name'], keep='last')
        new_mem_df.to_csv(MEMORY_FILE, index=False)
        print(f"Added {len(new_memory_entries)} new decisions to {MEMORY_FILE}.")

if __name__ == "__main__":
    main()