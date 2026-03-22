import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


class SyntheticJourneyGenerator:
    """
    Generates synthetic customer journey data using an enhanced Markov transition model.
    Mimics features from real-world clickstream datasets like e-shop clothing 2008.
    """

    def __init__(self, avg_session_length: int = 10):
        # Base states
        self.base_states = [
            'Home',
            'Search',
            'Product',  # We will expand this to specific products
            'Cart',
            'Checkout',
            'Exit'
        ]

        # Categories for products
        self.categories = ['Trousers', 'Skirts', 'Blouses', 'Sales']
        self.locations = ['Poland', 'Other European Countries']
        
        # Expanded states: Base states + Category-specific product pages
        self.states = [
            'Home', 'Search', 'Cart', 'Checkout', 'Exit'
        ] + [f'Product_{cat}' for cat in self.categories]

        # Transition probabilities
        # Rows: current state -> Columns: next state probabilities
        # We'll build this dynamically to handle multiple product categories
        self.transition_matrix = self._build_transition_matrix()
        
        self.avg_session_length = avg_session_length

    def _build_transition_matrix(self) -> Dict[str, Dict[str, float]]:
        matrix = {}
        
        # Probability distributions for base states
        base_probs = {
            'Home':     {'Search': 0.4, 'Product': 0.3, 'Cart': 0.05, 'Checkout': 0.05, 'Exit': 0.1, 'Home': 0.1},
            'Search':   {'Home': 0.1, 'Search': 0.2, 'Product': 0.4, 'Cart': 0.1, 'Checkout': 0.05, 'Exit': 0.15},
            'Cart':     {'Home': 0.05, 'Search': 0.05, 'Product': 0.1, 'Cart': 0.1, 'Checkout': 0.6, 'Exit': 0.1},
            'Checkout': {'Checkout': 1.0}, # Absorbing
            'Exit':     {'Exit': 1.0}      # Absorbing
        }

        # For states that can lead to 'Product', we split the 'Product' prob across categories
        for state, targets in base_probs.items():
            matrix[state] = {}
            prod_prob = targets.get('Product', 0)
            
            # Map simple targets
            for target, prob in targets.items():
                if target != 'Product':
                    matrix[state][target] = prob
            
            # Distribute product probability
            if prod_prob > 0:
                for cat in self.categories:
                    matrix[state][f'Product_{cat}'] = prod_prob / len(self.categories)

        # Probabilities for Product states
        for cat in self.categories:
            state_name = f'Product_{cat}'
            matrix[state_name] = {
                'Home': 0.05,
                'Search': 0.15,
                'Cart': 0.4,
                'Checkout': 0.05,
                'Exit': 0.2,
                state_name: 0.1, # Viewing another product in same category
            }
            # Small chance to jump to another category product
            other_cats = [c for c in self.categories if c != cat]
            for o_cat in other_cats:
                matrix[state_name][f'Product_{o_cat}'] = 0.05 / len(other_cats)

        return matrix

    def generate(self, num_sessions: int = 1000, seed: int | None = None) -> pd.DataFrame:
        """
        Generate synthetic clickstream data with rich attributes.
        """
        rng = np.random.default_rng(seed)
        data = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)

        for session_id in range(num_sessions):
            current_state = 'Home'
            step = 1
            location = rng.choice(self.locations)
            
            # Session-start time
            state_time = base_time + timedelta(minutes=int(rng.integers(0, 43200))) # Within a month
            
            max_steps = max(2, int(rng.poisson(self.avg_session_length)))

            while current_state not in ['Checkout', 'Exit'] and step <= max_steps:
                targets = list(self.transition_matrix[current_state].keys())
                probs = list(self.transition_matrix[current_state].values())
                
                # Ensure they sum to 1 due to floating point
                probs = np.array(probs) / np.sum(probs)
                
                next_state = rng.choice(targets, p=probs)

                # Generate attributes
                category = 'None'
                price = 0.0
                if 'Product' in current_state:
                    category = current_state.split('_')[1]
                    price = round(float(rng.uniform(10.0, 500.0)), 2)
                
                data.append({
                    'session_id': session_id,
                    'step': step,
                    'timestamp': state_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'location': location,
                    'source': current_state,
                    'target': next_state,
                    'category': category,
                    'price': price,
                    'is_high_price': 1 if price > 200 else 0
                })

                current_state = next_state
                step += 1
                state_time += timedelta(seconds=int(rng.integers(5, 300))) # Time between clicks

        return pd.DataFrame(data)


def main():
    print("Generating enhanced synthetic dataset...")
    generator = SyntheticJourneyGenerator(avg_session_length=12)
    df = generator.generate(num_sessions=2000, seed=42)

    output_file = Path(__file__).resolve().parent / "enhanced_synthetic_journey.csv"
    df.to_csv(output_file, index=False)

    print(f"Success! Saved to {output_file}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nSample Data:")
    print(df.head(10))


if __name__ == "__main__":
    main()
