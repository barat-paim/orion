import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

class PhotoClusterer:
    def __init__(self):
        self.scaler = StandardScaler()
        self.clusterer = DBSCAN(eps=0.3, min_samples=2)

    def cluster_photos(self, photos, zoom_level):
        if len(photos) < 2:
            return photos

        # Convert photos to a DataFrame
        df = pd.DataFrame([(p['latitude'], p['longitude']) for p in photos], columns=['latitude', 'longitude'])
        gdf = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df.longitude, df.latitude)])

        # Scale the coordinates
        coords = self.scaler.fit_transform(df[['latitude', 'longitude']])

        # Adjust eps based on zoom level
        eps = self._calculate_eps(zoom_level)
        self.clusterer.set_params(eps=eps)

        # Perform clustering
        clusters = self.clusterer.fit_predict(coords)

        # Add cluster information to the GeoDataFrame
        gdf['cluster'] = clusters

        # Calculate cluster centroids
        centroids = gdf[gdf['cluster'] != -1].groupby('cluster').agg({
            'geometry': lambda x: x.unary_union.centroid,
            'latitude': 'mean',
            'longitude': 'mean'
        }).reset_index()

        # Prepare the result
        result = []
        for _, centroid in centroids.iterrows():
            cluster_photos = gdf[gdf['cluster'] == centroid['cluster']]
            result.append({
                'latitude': centroid['latitude'],
                'longitude': centroid['longitude'],
                'count': len(cluster_photos),
                'photos': cluster_photos.to_dict('records')
            })

        # Add unclustered photos
        unclustered = gdf[gdf['cluster'] == -1]
        for _, photo in unclustered.iterrows():
            result.append({
                'latitude': photo['latitude'],
                'longitude': photo['longitude'],
                'count': 1,
                'photos': [photo.to_dict()]
            })

        return result

    def _calculate_eps(self, zoom_level):
        # Adjust this function based on your specific needs
        return max(0.1, 1.0 / (zoom_level + 1))