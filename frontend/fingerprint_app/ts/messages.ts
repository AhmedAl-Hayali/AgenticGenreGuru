export const Messages = {
  noResults:
    "No results found.\nMake sure everything is spelled correctly, or try searching for something different.",
  searchNetworkDown:
    "Network disconnected. The search service is unreachable — please try again later.",
  confirmNetworkDown:
    "Network disconnected. The fingerprint could not be generated — please try again later.",
  genericSearch: "Search failed. Please try again.",
  genericConfirm: "Could not confirm this match. Please try again.",
  emptyQuery: "Enter a song title to search.",
  searching: "Searching…",
  fingerprintStored: "Fingerprint stored successfully.",
  foundMatches: (count: number) =>
    `Found ${count} match${count === 1 ? "" : "es"}. ` +
    "Click a match once to select, then click it again to confirm.",
  selectedMatch: (title: string) =>
    `Selected "${title}". Click it again to confirm and fingerprint it.`,
  fetching: (title: string) => `Fetching the audio preview and fingerprinting "${title}"…`,
  audioUnprocessable: (title: string) =>
    `The audio file cannot be processed — "${title}" could not be fingerprinted.`,
  badgeSelected: "Selected",
  unknownArtist: "Unknown artist",
  fingerprintDefaultTitle: "Fingerprint stored",
  rows: {
    songId: "Song ID",
    deezerId: "Deezer ID",
    isrc: "ISRC",
    vectorLength: "Vector Length",
  },
};
