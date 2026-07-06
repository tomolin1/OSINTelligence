import React from 'react';

export default function SearchPanel({ search, onSearch, entities, selected, onSelect, colors, names }) {
  return (
    <div className="left-panel">
      <div className="search-box">
        <input
          type="text"
          placeholder="搜索组织、恶意软件、CVE..."
          value={search}
          onChange={e => onSearch(e.target.value)}
          autoFocus
        />
      </div>
      <div className="entity-list">
        {entities.map(n => (
          <div
            key={n.id}
            className={`entity-item${selected?.id === n.id ? ' active' : ''}`}
            onClick={() => onSelect(n)}
          >
            <div className="entity-dot" style={{ background: colors[n.type] || '#666' }}></div>
            <div className="entity-info">
              <div className="entity-name">{n.name}</div>
              <div className="entity-type">{names[n.type] || n.type}</div>
            </div>
            <div className="entity-conf">{n.confidence.toFixed(2)}</div>
          </div>
        ))}
        {entities.length === 0 && (
          <div style={{ padding: 20, textAlign: 'center', color: '#6e7681', fontSize: 13 }}>无匹配结果</div>
        )}
      </div>
    </div>
  );
}
