/**
 * Convert SAN notation to plain English.
 * "Bxe7" → "Bishop takes on e7"
 * "Nf3" → "Knight to f3"  
 * "e4" → "Pawn to e4"
 * "O-O" → "Castles kingside"
 */

const PIECE_NAMES: Record<string, string> = {
  K: "King",
  Q: "Queen",
  R: "Rook",
  B: "Bishop",
  N: "Knight",
};

export function sanToEnglish(san: string): string {
  if (!san) return "";

  // Remove check/mate symbols
  const clean = san.replace(/[+#!?]/g, "").trim();

  if (clean === "O-O") return "Castles kingside";
  if (clean === "O-O-O") return "Castles queenside";

  // Piece moves: e.g. Nf3, Bxe7, Qd1, Raxf1, Nbd2
  const pieceMatch = clean.match(/^([KQRBN])([a-h]?)([1-8]?)(x?)([a-h][1-8])(=[QRBN])?$/);
  if (pieceMatch) {
    const [, piece, , , captures, square, promotion] = pieceMatch;
    const name = PIECE_NAMES[piece] || piece;
    let desc = captures ? `${name} takes on ${square}` : `${name} to ${square}`;
    if (promotion) desc += `, promotes to ${PIECE_NAMES[promotion[1]] || promotion[1]}`;
    return desc;
  }

  // Pawn moves: e4, exd5, e8=Q
  const pawnMatch = clean.match(/^([a-h]?)(x?)([a-h][1-8])(=[QRBN])?$/);
  if (pawnMatch) {
    const [, , captures, square, promotion] = pawnMatch;
    let desc = captures ? `Pawn takes on ${square}` : `Pawn to ${square}`;
    if (promotion) desc += `, promotes to ${PIECE_NAMES[promotion[1]] || promotion[1]}`;
    return desc;
  }

  return san;
}

/** Describe why a move was suboptimal in plain English */
export function describeInsight(
  playedSan: string,
  bestSan: string,
  classification: string,
): string {
  const played = sanToEnglish(playedSan);
  const best = sanToEnglish(bestSan);
  
  const severity = classification === "blunder" ? "a blunder"
    : classification === "mistake" ? "a mistake"
    : "an inaccuracy";

  return `${played} was ${severity}. ${best} was the better move.`;
}
