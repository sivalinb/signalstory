from html import escape


def milestone(report):
    n = len(report["badges"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
    <rect width="1200" height="630" rx="28" fill="#102631"/><circle cx="1080" cy="70" r="245" fill="#194746"/>
    <text x="70" y="100" fill="#80f0ce" font-family="sans-serif" font-size="30" font-weight="700">SignalStory</text>
    <text x="70" y="183" fill="#accbc9" font-family="sans-serif" font-size="20">MY LEARNING MILESTONE</text>
    <text x="70" y="284" fill="#ffffff" font-family="sans-serif" font-size="66" font-weight="700">{n} missions completed.</text>
    <text x="70" y="369" fill="#80f0ce" font-family="sans-serif" font-size="40">{report["concepts_practiced"]} concepts practiced · {n * 100} XP</text>
    <text x="70" y="460" fill="#d3e6e4" font-family="sans-serif" font-size="25">Understand the signal. Explain the story.</text>
    <text x="70" y="540" fill="#9dbdbd" font-family="sans-serif" font-size="17">Practice evidence · Independent learning · No accredited certification claim</text>
    <text x="70" y="585" fill="#80f0ce" font-family="sans-serif" font-size="18">{escape("github.com/sivalinb/signalstory")}</text></svg>"""
