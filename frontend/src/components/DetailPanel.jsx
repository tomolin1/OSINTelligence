import React from 'react';
import { mockData } from '../data';

export default function DetailPanel({ node, colors, names }) {
  if (!node) {
    return (
      <div className="right-panel">
        <div className="empty-detail">
          <div className="icon">🔍</div>
          <div>选择一个实体查看详情</div>
        </div>
      </div>
    );
  }

  const p = node.properties || {};
  const rels = mockData.edges.filter(e => e.source === node.id || e.target === node.id);
  const typeTagClass = {
    APT_GROUP: 'tag-apt', MALWARE: 'tag-malware', CVE: 'tag-cve',
    COUNTRY: 'tag-country', INDUSTRY: 'tag-industry',
    TECHNIQUE: 'tag-technique', TOOL: 'tag-org', PERSON: 'tag-org',
    CAMPAIGN: 'tag-cve', ORGANIZATION: 'tag-org',
  };

  const getRelatedName = (edge, side) => {
    const tid = side === 'out' ? edge.target : edge.source;
    const n = mockData.nodes.find(x => x.id === tid);
    return n ? n.name : tid.slice(0, 16);
  };

  return (
    <div className="right-panel">
      <div className="detail-header">
        <h2>{node.name}</h2>
        <div className="detail-tags">
          <span className={`tag ${typeTagClass[node.type] || 'tag-org'}`}>{names[node.type] || node.type}</span>
          {p.origin_country && <span className="tag tag-country">{p.origin_country}</span>}
        </div>
      </div>
      <div className="detail-stats">
        <div className="stat-box">
          <div className="stat-value">{(node.confidence * 100).toFixed(0)}%</div>
          <div className="stat-label">置信度</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{rels.length}</div>
          <div className="stat-label">关联关系</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{p.active_years || '-'}</div>
          <div className="stat-label">活跃周期</div>
        </div>
      </div>
      <div className="detail-section">
        <h3>📋 简介</h3>
        <p>{node.description || '暂无描述'}</p>
        {p.aliases?.length > 0 && (
          <p style={{ fontSize: 12, color: '#6e7681', marginTop: 6 }}>别名：{p.aliases.join(' / ')}</p>
        )}
      </div>
      <div className="detail-section">
        <h3>🔗 关联关系 ({rels.length})</h3>
        {rels.map(r => {
          const isOut = r.source === node.id;
          const relatedName = getRelatedName(r, isOut ? 'out' : 'in');
          const related = mockData.nodes.find(n => n.id === (isOut ? r.target : r.source));
          return (
            <div className="rel-item" key={r.id}>
              <div className="rel-dot" style={{ background: colors[related?.type || ''] || '#666' }}></div>
              <span>{isOut ? `${node.name} → ${relatedName}` : `${relatedName} → ${node.name}`}</span>
              <span className="rel-label">{r.label}</span>
              <span className="rel-conf">{(r.confidence * 100).toFixed(0)}%</span>
            </div>
          );
        })}
        {rels.length === 0 && <p style={{ fontSize: 12, color: '#6e7681' }}>暂无关联关系</p>}
      </div>
      <div className="detail-section">
        <h3>🏷️ 属性</h3>
        {Object.entries(p).filter(([k]) => k !== 'aliases').map(([k, v]) => (
          <div className="rel-item" key={k}>
            <span style={{ color: '#8b949e', minWidth: 90 }}>{k}</span>
            <span style={{ color: '#c9d1d9' }}>{Array.isArray(v) ? v.join(', ') : String(v)}</span>
          </div>
        ))}
      </div>
      <div className="detail-actions">
        <button className="btn-primary" onClick={() => alert(`生成 ${node.name} 的威胁分析报告`)}>
          📄 生成报告
        </button>
        <button className="btn-secondary" onClick={() => alert('导出图谱为图片')}>
          📤 导出
        </button>
      </div>
    </div>
  );
}
