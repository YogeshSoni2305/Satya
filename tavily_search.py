import requests
import json

def tavily_search(
    query: str,
    topic: str = "news",
    search_depth: str = "advanced",
    max_results: int = 10,
    include_domains: list = None,
    exclude_domains: list = None,
    include_answer: bool = True,
    include_raw_content: bool = True,
    TAVILY_API_KEY: str = None,
    save_to_file: str = None
):
    """
    Search Tavily API for fact-checking or news data.
    Compatible with ClaimFighter pipeline.
    """
    url = "https://api.tavily.com/search"

    payload = {
        "query": query,
        "topic": topic,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_domains": include_domains or [],
        "exclude_domains": exclude_domains or [],
        "include_answer": include_answer,
        "include_raw_content": include_raw_content,
    }

    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Tavily API Error: {response.status_code}, {response.text}")

        response_json = response.json()

        if save_to_file:
            with open(save_to_file, "w", encoding="utf-8") as file:
                json.dump(response_json, file, indent=4, ensure_ascii=False)
            print(f"🟢 Tavily response saved to {save_to_file}")

        return response_json

    except Exception as e:
        print(f"[TAVILY ERROR] {e}")
        return {}
