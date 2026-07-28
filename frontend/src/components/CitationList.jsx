export default function CitationList({ citations, precedentSections }) {
  if (citations.length === 0) return null;

  return (
    <div className="precedent-log">
      <span className="precedent-log__eyebrow">PRECEDENT LOG</span>
      {citations.map((c) => {
        const section = precedentSections.find((s) => s.heading === c.source);
        return (
          <div className="precedent-log__item" key={c.source}>
            <span className="precedent-log__marker">▸</span>
            <div>
              <div className="precedent-log__source">{c.source}</div>
              <p className="precedent-log__text">{section ? section.text : c.snippet}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
