def longest_common_substring(titles, threshold=0.6):
    """Find the longest common substring from a list of titles."""
    # Get all possible substrings from all titles
    all_substrings = {}
    for title in titles:
        for substring in get_all_substrings(title):
            if substring not in all_substrings:
                # Count in how many titles this substring appears
                count = sum(1 for t in titles if substring in t)
                frequency = count / len(titles)
                if frequency >= threshold:
                    all_substrings[substring] = frequency

    if not all_substrings:
        return ""

    # Find the longest substring that meets the threshold
    candidates = sorted(
        all_substrings.items(), key=lambda x: len(x[0]), reverse=True
    )

    return candidates[0][0].strip() if candidates else titles[0]

def get_all_substrings(string):
    """Get all possible substrings of length > 2 from a string."""
    substrings = []
    for i in range(len(string)):
        for j in range(i + 1, len(string) + 1):
            substring = string[i:j]
            if len(substring) > 2:  # Only consider substrings longer than 2 chars
                substrings.append(substring)
    return substrings