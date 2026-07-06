import React, { useState, useMemo } from 'react';
import SearchPanel from './components/SearchPanel';
import GraphChart from './components/GraphChart';
import DetailPanel from './components/DetailPanel';
import { mockData, TYPE_COLORS, TYPE_NAMES } from './data';

export default function App() {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [graphCenter, setGraphCenter] = useState('ENT_APT_GROUP_apt28_001');

  const entities = useMemo(() => {
    const kw = search.toLowerCase();
    return mockData.nodes.filter(n =>
      n.name.toLowerCase().includes(kw) ||
      n.type.toLowerCase().includes(kw) ||
      (n.properties?.aliases || []).some(a => a.toLowerCase().includes(kw))
    ).slice(0, 50);
  }, [search]);

  const handleSelect = (node) => {
    setSelected(node);
    setGraphCenter(node.id);
  };

  const edges = mockData.edges.filter(e =>
    e.source === graphCenter || e.target === graphCenter
  );

  const graphNodes = useMemo(() => {
    const connected = new Set();
    connected.add(graphCenter);
    edges.forEach(e => { connected.add(e.source); connected.add(e.target); });
    return mockData.nodes.filter(n => connected.has(n.id));
  }, [graphCenter, edges]);

  return (
    <>
      <div className="topbar">
        <h1>🛡️ <span>OSINT</span>elligence <span className="badge">MVP</span></h1>
        <div className="stats">
          <span><span className="dot green"></span>图谱就绪</span>
          <span>{mockData.nodes.length} 节点 · {mockData.edges.length} 条边</span>
        </div>
      </div>
      <div className="app-body">
        <SearchPanel
          search={search}
          onSearch={setSearch}
          entities={entities}
          selected={selected}
          onSelect={handleSelect}
          colors={TYPE_COLORS}
          names={TYPE_NAMES}
        />
        <div className="center-panel">
          <div className="graph-wrapper">
            <GraphChart
              nodes={graphNodes}
              edges={edges}
              selectedId={graphCenter}
              onNodeClick={handleSelect}
              colors={TYPE_COLORS}
            />
          </div>
          <div className="graph-legend">
            {Object.entries(TYPE_NAMES).map(([type, name]) => (
              <div className="legend-item" key={type}>
                <div className="legend-dot" style={{ background: TYPE_COLORS[type] || '#666' }}></div>
                {name}
              </div>
            ))}
          </div>
        </div>
        <DetailPanel node={selected} colors={TYPE_COLORS} names={TYPE_NAMES} />
      </div>
    </>
  );
}
