import requests
from pprint import pprint
import hashlib
import json
from datetime import datetime
import urllib.parse

#retrieved 306 products

# Define the API endpoint and headers
url = "https://princesspollydev.myshopify.com/api/2024-04/graphql"
headers = {
    'content-type': 'application/json',  # Send as JSON
    'accept': 'application/json',
    'x-shopify-storefront-access-token': 'f6e88f0840c54eb2024ab6fea4d5622e',
}

# GraphQL query with variables for pagination and product limit
query = '''
query GetProducts($numProducts: Int!, $cursor: String) @inContext(country:US, language:EN) {
    collection(id: "gid://shopify/Collection/128423067732") {
        products(first: $numProducts, after: $cursor, reverse: false) {
            pageInfo {
                hasNextPage
                endCursor
            }
            edges {
                node {
                    id
                    title
                    handle
                    tags
                    productType
                    onlineStoreUrl
                    availableForSale
                    vendor
                    options {
                        name
                        values
                    }
                    variants(first: 1) {
                        edges {
                            node {
                                id
                                title
                                price {
                                    amount
                                    currencyCode
                                }
                                compareAtPrice {
                                    amount
                                    currencyCode
                                }
                                image {
                                    url(transform: {maxHeight: 500})
                                    altText
                                }
                                availableForSale
                            }
                        }
                    }
                    images(first: 1) {
                        edges {
                            node {
                                url(transform: {maxHeight: 500})
                                altText
                            }
                        }
                    }
                }
            }
        }
    }
}
'''

# Initialize variables for pagination
all_products = []  # To store all fetched products
cursor = None  # Start without a cursor
has_next_page = True
previous_cursor = None  # Track the previous cursor to prevent infinite loops

# Loop until there are no more pages
while has_next_page:
    variables = {
        "numProducts": 16,
        "cursor": cursor
    }

    # Send the request
    response = requests.post(url, headers=headers, json={
        'query': query,
        'variables': variables
    })

    # Parse the response
    data = response.json()
    print(data)  # Optionally print the full response

    # Check for valid products data
    if 'data' in data and data['data']['collection']:
        products = data['data']['collection']['products']['edges']
        all_products.extend(products)  # Add current page of products to the list

        # Get pagination info
        page_info = data['data']['collection']['products']['pageInfo']
        has_next_page = page_info['hasNextPage']
        end_cursor = page_info['endCursor']  # Update the cursor for the next page

        # Check if end_cursor has changed to avoid infinite loops
        if cursor == end_cursor:
            print("Cursor hasn't changed. Stopping the loop to avoid infinite loop.")
            break

        # Update cursor and track previous cursor
        previous_cursor = cursor
        cursor = end_cursor

        print(f"Retrieved {len(products)} products on this page.")
        print(f"Total products retrieved so far: {len(all_products)}")
        if has_next_page:
            print(f"End cursor for next page: {cursor}")
        else:
            print("No more pages left.")
    else:
        print("No more products or query failed.")
        break

print(f"Total products retrieved: {len(all_products)}")

#took the response from this, and converted it to json format. and then passed the json to the below function to get the output. gives all
#categories not marked optional in the check product function. 


def convert_shopify_to_standard(shopify_data, retailer):
    standard_products = []
    edges = shopify_data['data']['collection']['products']['edges']
    
    for edge in edges:
        node = edge['node']
        
        # Generate product hash
        original_url = node['onlineStoreUrl']
        product_hash = hashlib.md5(original_url.encode()).hexdigest()[:10]
        
        # Create the standardized product object
        product = {
            'id': f"{retailer}_{node['id'].split('/')[-1]}",
            'originalUrl': original_url,
            'productHash': product_hash,
            'url': f"https://scout.shop/p/{product_hash}?url={urllib.parse.quote(original_url)}",
            'brand': node['vendor'],
            'retailer': retailer.lower().replace(' ', '_'),
            'formatted_retailer': retailer,
            'title': node['title'],
            'description': node.get('description', ''),
            'price': {
                'currentPrice': node['variants']['edges'][0]['node']['price']['amount'],
                'currency': node['variants']['edges'][0]['node']['price']['currencyCode'],
                'originalPrice': node['variants']['edges'][0]['node']['compareAtPrice']['amount'] if node['variants']['edges'][0]['node']['compareAtPrice'] else node['variants']['edges'][0]['node']['price']['amount'],
                'isDiscounted': node['variants']['edges'][0]['node']['compareAtPrice'] is not None,
                'lastPriceChange': datetime.now().isoformat(),
                'pricePercentageChange': round((float(node['variants']['edges'][0]['node']['compareAtPrice']['amount']) - float(node['variants']['edges'][0]['node']['price']['amount'])) / float(node['variants']['edges'][0]['node']['compareAtPrice']['amount']), 3) if node['variants']['edges'][0]['node']['compareAtPrice'] else 0
            },
            'priceHistory': [],  # This would need to be populated from historical data
            'images': [img['node']['url'] for img in node['images']['edges']],
            'color': {
                'name': node['options'][1]['values'][0] if len(node['options']) > 1 else '',
                'swatch': ''  # Shopify data doesn't provide swatch URLs
            },
            'sizes': {
                'allSizes': node['options'][0]['values'],
                'availableSizes': [variant['node']['title'].split(' / ')[0] for variant in node['variants']['edges'] if variant['node']['availableForSale']],
                'sizingInfo': {}
            },
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat(),
            'gender': 'W' if any(tag.lower() in ['women', 'womens', 'woman', "women's"] for tag in node['tags']) else 'M',
            'tags': node['tags'],
            'category': node['productType'],
            'popularityData': {},
            'reviewData': {
                'rating': '',
                'numReviews': '',
                'individualReviews': []
            },
            'additionalInfo': {}
        }
        
        standard_products.append(product)
    
    return standard_products

# Example usage:
with open('env/ourjson.json', 'r') as f:
   shopify_data = json.load(f)
   standardized_products = convert_shopify_to_standard(shopify_data, 'Princess Polly')

 # Print or process the standardized products as needed
for product in standardized_products:
    print(json.dumps(product, indent=2))


#This prints out the data with all the categories in the schema not marked optional. 
#ourjson.json was the file with the response converted to json.

#Output:
{
  "id": "Princess Polly_6970387562580",
  "originalUrl": "https://us.princesspolly.com/products/reynard-shorts-black",
  "productHash": "91aa05efbb",
  "url": "https://scout.shop/p/91aa05efbb?url=https%3A//us.princesspolly.com/products/reynard-shorts-black",
  "brand": "Princess Polly",
  "retailer": "princess_polly",
  "formatted_retailer": "Princess Polly",
  "title": "Reynard Shorts Black",
  "description": "",
  "price": {
    "currentPrice": "22.0",
    "currency": "USD",
    "originalPrice": "44.0",
    "isDiscounted": true,
    "lastPriceChange": "2024-09-04T18:26:55.046281",
    "pricePercentageChange": 0.5
  },
  "priceHistory": [],
  "images": [
    "https://cdn.shopify.com/s/files/1/0061/8627/0804/files/1-modelinfo-elly-us2_e47ae004-362a-46d1-877d-c9080601541a_x500.jpg?v=1718946177"
  ],
  "color": {
    "name": "Black",
    "swatch": ""
  },
  "sizes": {
    "allSizes": [
      "US 0",
      "US 2",
      "US 4",
      "US 6",
      "US 8",
      "US 10",
      "US 12"
    ],
    "availableSizes": [
      "US 0"
    ],
    "sizingInfo": {}
  },
  "createdAt": "2024-09-04T18:26:55.046291",
  "updatedAt": "2024-09-04T18:26:55.046292",
  "gender": "M",
  "tags": [
    "50%",
    "Beach Shorts",
    "Black Shorts",
    "bottoms",
    "Festival",
    "festival shorts",
    "In Stock",
    "Live",
    "Model Elly",
    "New Arrivals",
    "New Arrivals - US",
    "PARTY",
    "Party goingout",
    "Party Season",
    "party shorts",
    "Relaxed",
    "Relaxed fit",
    "Sale",
    "sale-20240819",
    "sale-tracked",
    "SH Shoot",
    "shorts",
    "Studio Shoot",
    "Style:Shorts",
    "Summer Shop",
    "summer shorts",
    "The Festival Shop"
  ],
  "category": "SHORTS",
  "popularityData": {},
  "reviewData": {
    "rating": "",
    "numReviews": "",
    "individualReviews": []
  },
  "additionalInfo": {}
}
{
  "id": "Princess Polly_6893204635732",
  "originalUrl": "https://us.princesspolly.com/products/barbuto-denim-wrap-mini-skirt-light-wash",
  "productHash": "69324860de",
  "url": "https://scout.shop/p/69324860de?url=https%3A//us.princesspolly.com/products/barbuto-denim-wrap-mini-skirt-light-wash",
  "brand": "Princess Polly",
  "retailer": "princess_polly",
  "formatted_retailer": "Princess Polly",
  "title": "Barbuto Denim Wrap Mini Skirt Light Wash",
  "description": "",
  "price": {
    "currentPrice": "27.0",
    "currency": "USD",
    "originalPrice": "54.0",
    "isDiscounted": true,
    "lastPriceChange": "2024-09-04T18:26:55.046306",
    "pricePercentageChange": 0.5
  },
  "priceHistory": [],
  "images": [
    "https://cdn.shopify.com/s/files/1/0061/8627/0804/files/0-modelinfo-alexa-us2_167c6162-38c8-43a1-8dbb-a2ef86de9ff9_x500.jpg?v=1714610099"
  ],
  "color": {
    "name": "Light Wash",
    "swatch": ""
  },
  "sizes": {
    "allSizes": [
      "US 0",
      "US 2",
      "US 4",
      "US 6",
      "US 8",
      "US 10",
      "US 12"
    ],
    "availableSizes": [],
    "sizingInfo": {}
  },
  "createdAt": "2024-09-04T18:26:55.046309",
  "updatedAt": "2024-09-04T18:26:55.046309",
  "gender": "M",
  "tags": [
    "2024 FESTIVAL COACHELLA",
    "2024 NH POOL PARTY",
    "2024 NH SPRING SHOP",
    "50%",
    "Broken Sizes Sale",
    "category:Skirts",
    "denim",
    "denim skirt",
    "Denim Skirts",
    "festival skirts",
    "In Stock",
    "Jean Skirt",
    "Limited Stock",
    "Live",
    "Mini Skirt",
    "Mini Skirts",
    "Model Alexa",
    "New Arrivals",
    "Sale",
    "sale-20240819",
    "sale-tracked",
    "SH Shoot",
    "Skirt",
    "Skirts",
    "spring skirt",
    "Studio Shoot",
    "Style:Mini Skirts",
    "subcategory:Mini Skirts",
    "SUMMER",
    "Summer Shop",
    "summer skirt",
    "summer skirts",
    "The Denim Shop",
    "Wrap",
    "Wrap Skirt"
  ],
  "category": "MINI SKIRTS",
  "popularityData": {},
  "reviewData": {
    "rating": "",
    "numReviews": "",
    "individualReviews": []
  },
  "additionalInfo": {}
}
