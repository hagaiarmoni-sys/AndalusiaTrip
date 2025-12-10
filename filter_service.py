"""
FilterService - Advanced filtering and search capabilities
"""
import pandas as pd
from typing import List, Dict, Optional


class FilterService:
    def __init__(self, attraction_service):
        """Initialize with attraction service"""
        self.attraction_service = attraction_service
    
    def filter(self, criteria: Dict) -> pd.DataFrame:
        """Filter attractions by multiple criteria"""
        df = self.attraction_service.get_all()
        
        # Filter by city
        if 'city' in criteria and criteria['city']:
            df = df[df['city'] == criteria['city']]
        
        # Filter by cities (multiple)
        if 'cities' in criteria and criteria['cities']:
            df = df[df['city'].isin(criteria['cities'])]
        
        # Filter by category
        if 'category' in criteria and criteria['category']:
            df = df[df['category'] == criteria['category']]
        
        # Filter by minimum rating
        if 'min_rating' in criteria:
            df = df[df['rating'] >= criteria['min_rating']]
        
        # Filter by rating range
        if 'rating_range' in criteria:
            min_r, max_r = criteria['rating_range']
            df = df[(df['rating'] >= min_r) & (df['rating'] <= max_r)]
        
        # Filter by duration range
        if 'duration_range' in criteria:
            min_d, max_d = criteria['duration_range']
            df = df[
                (df['visit_duration_hours'] >= min_d) &
                (df['visit_duration_hours'] <= max_d)
            ]
        
        # Filter by tags
        if 'tags' in criteria and criteria['tags']:
            mask = df['tags'].apply(
                lambda tags: any(
                    any(tag.lower() in t.lower() for tag in criteria['tags'])
                    for t in tags
                )
            )
            df = df[mask]
        
        # Filter by free entrance
        if criteria.get('free_only', False):
            mask = df['entrance_fee'].str.lower().str.contains('free')
            df = df[mask]
        
        # Filter by booking requirement
        if 'booking_required' in criteria:
            df = df[df['advance_booking'] == criteria['booking_required']]
        
        # Filter by search query
        if 'search' in criteria and criteria['search']:
            query = criteria['search'].lower()
            mask = (
                df['name'].str.lower().str.contains(query, na=False) |
                df['description'].str.lower().str.contains(query, na=False) |
                df['tags'].apply(lambda tags: any(query in t.lower() for t in tags))
            )
            df = df[mask]
        
        return df
    
    def sort(self, df: pd.DataFrame, sort_by: str = 'rating', 
             order: str = 'desc') -> pd.DataFrame:
        """Sort attractions by various criteria"""
        ascending = (order == 'asc')
        
        if sort_by == 'rating':
            return df.sort_values('rating', ascending=ascending)
        elif sort_by == 'duration':
            return df.sort_values('visit_duration_hours', ascending=ascending)
        elif sort_by == 'name':
            return df.sort_values('name', ascending=ascending)
        elif sort_by == 'city':
            return df.sort_values('city', ascending=ascending)
        else:
            return df
    
    def filter_and_sort(self, criteria: Dict, sort_by: str = 'rating',
                       order: str = 'desc') -> pd.DataFrame:
        """Filter and sort in one operation"""
        filtered = self.filter(criteria)
        return self.sort(filtered, sort_by, order)
    
    def group_by_city(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group attractions by city"""
        return {city: group for city, group in df.groupby('city')}
    
    def group_by_category(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group attractions by category"""
        return {cat: group for cat, group in df.groupby('category')}
    
    def get_recommendations(self, preferences: Dict) -> pd.DataFrame:
        """Get attractions matching user preferences"""
        favorite_categories = preferences.get('favorite_categories', [])
        min_rating = preferences.get('min_rating', 8.5)
        max_duration = preferences.get('max_duration', 4)
        prefer_free = preferences.get('prefer_free', False)
        cities = preferences.get('cities', [])
        
        criteria = {
            'min_rating': min_rating,
            'duration_range': (0, max_duration)
        }
        
        if cities:
            criteria['cities'] = cities
        
        if prefer_free:
            criteria['free_only'] = True
        
        # Get attractions from favorite categories
        if favorite_categories:
            dfs = []
            for cat in favorite_categories:
                cat_df = self.attraction_service.get_by_category(cat)
                dfs.append(cat_df)
            
            if dfs:
                df = pd.concat(dfs).drop_duplicates()
                
                # Apply other filters
                if cities:
                    df = df[df['city'].isin(cities)]
                df = df[df['rating'] >= min_rating]
                df = df[df['visit_duration_hours'] <= max_duration]
                if prefer_free:
                    mask = df['entrance_fee'].str.lower().str.contains('free')
                    df = df[mask]
                
                return df.sort_values('rating', ascending=False)
        
        return self.filter_and_sort(criteria, 'rating', 'desc')
    
    def find_similar(self, attraction_id: str, limit: int = 5) -> pd.DataFrame:
        """Find similar attractions"""
        attraction = self.attraction_service.get_by_id(attraction_id)
        if not attraction:
            return pd.DataFrame()
        
        all_attractions = self.attraction_service.get_all()
        all_attractions = all_attractions[all_attractions['id'] != attraction_id]
        
        # Calculate similarity score
        def calculate_score(row):
            score = 0
            
            # Same category
            if row['category'] == attraction['category']:
                score += 3
            
            # Same city
            if row['city'] == attraction['city']:
                score += 2
            
            # Similar tags
            common_tags = set(row['tags']) & set(attraction['tags'])
            score += len(common_tags)
            
            # Similar rating
            if abs(row['rating'] - attraction['rating']) < 0.5:
                score += 1
            
            return score
        
        all_attractions['similarity_score'] = all_attractions.apply(
            calculate_score, axis=1
        )
        
        similar = all_attractions[all_attractions['similarity_score'] > 0]
        similar = similar.sort_values('similarity_score', ascending=False)
        
        return similar.head(limit)