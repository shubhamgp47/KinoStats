import JSZip from "jszip";
import Papa from "papaparse";
import type { LetterboxdImportEntry } from "../../types/api";

interface RawDiaryRow {
  Date?: string;
  Name?: string;
  Year?: string;
  "Letterboxd URI"?: string;
  Rating?: string;
  Rewatch?: string;
}

interface RawWatchedRow {
  Date?: string;
  Name?: string;
  Year?: string;
  "Letterboxd URI"?: string;
}

export async function parseLetterboxdFile(
  file: File
): Promise<{ entries: LetterboxdImportEntry[] }> {
  if (file.name.endsWith(".zip")) {
    const zip = new JSZip();
    const contents = await zip.loadAsync(file);

    const diaryFile = contents.file(/(^|\/)diary\.csv$/i)[0];
    const watchedFile = contents.file(/(^|\/)watched\.csv$/i)[0];

    if (!diaryFile && !watchedFile) {
      throw new Error("Could not find diary.csv or watched.csv in the archive.");
    }

    const diaryEntries = diaryFile ? await parseDiaryCsv(await diaryFile.async("string")) : [];
    const watchedEntries = watchedFile ? await parseWatchedCsv(await watchedFile.async("string")) : [];


    // 1. Map diary entries first using (title + year + date) to preserve all legitimate rewatches
    const diaryMap = new Map<string, LetterboxdImportEntry>();
    const filmsWithDiaryEntries = new Set<string>();

    for (const entry of diaryEntries) {
      // Event Key: Preserves multiple diary viewings on different calendar dates
      const eventKey = `${entry.title.toLowerCase()}_${entry.releaseYear}_${entry.watchedDate}`;
      diaryMap.set(eventKey, entry);

      // Mark film as accounted for in diary
      filmsWithDiaryEntries.add(`${entry.title.toLowerCase()}_${entry.releaseYear}`);
    }

    // 2. Add watched.csv entries ONLY if the user never logged that film in diary.csv
    const cumulativeEntries: LetterboxdImportEntry[] = [];

    for (const entry of watchedEntries) {
      const catalogKey = `${entry.title.toLowerCase()}_${entry.releaseYear}`;
      
      // If not already present in the diary, add this historical watch
      if (!filmsWithDiaryEntries.has(catalogKey)) {
        cumulativeEntries.push(entry);
        filmsWithDiaryEntries.add(catalogKey); // Prevent duplicates within watched.csv itself
      }
    }

    // 3. Combine both collections: non-diary lifetime views + full diary timeline
    const allEntries = [...Array.from(diaryMap.values()), ...cumulativeEntries];

    return { entries: allEntries };
  } else {
    throw new Error("Unsupported format. Please upload a .zip archive or .csv file.");
  }
}

function parseDiaryCsv(csvContent: string): Promise<LetterboxdImportEntry[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<RawDiaryRow>(csvContent, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const entries: LetterboxdImportEntry[] = results.data
          .filter((row) => row.Name && row.Year)
          .map((row) => ({
            title: (row.Name || "").trim(),
            releaseYear: parseInt(row.Year || "0", 10),
            watchedDate: row.Date || new Date().toISOString().split("T")[0],
            rating: row.Rating && row.Rating.trim() !== "" ? parseFloat(row.Rating) : null,
            isRewatch: row.Rewatch?.toLowerCase() === "yes",
            letterboxdUri: row["Letterboxd URI"] || "",
          }));
        resolve(entries);
      },
      error: (err: Error) => reject(err),
    });
  });
}

function parseWatchedCsv(csvContent: string): Promise<LetterboxdImportEntry[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<RawWatchedRow>(csvContent, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const entries: LetterboxdImportEntry[] = results.data
          .filter((row) => row.Name && row.Year)
          .map((row) => ({
            title: (row.Name || "").trim(),
            releaseYear: parseInt(row.Year || "0", 10),
            watchedDate: row.Date || `${row.Year}-01-01`,
            rating: null,
            isRewatch: false,
            letterboxdUri: row["Letterboxd URI"] || "",
          }));
        resolve(entries);
      },
      error: (err: Error) => reject(err),
    });
  });
}