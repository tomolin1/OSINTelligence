import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function GraphChart({ nodes, edges, selectedId, onNodeClick, colors }) {
  const option = useMemo(() => ({
    tooltip: {
      trigger: 'item',
      formatter: params => {
        if (params.dataType === 'node') {
          const d = params.data;
          return `<strong>${d.name}</strong><br/>类型: ${d._type}<br/>置信度: ${(d._conf * 100).toFixed(0)}%<br/>${d._desc || ''}`;
        }
        return params.data?.label || '';
      },
      backgroundColor: '#161b22',
      borderColor: '#30363d',
      textStyle: { color: '#e6edf3', fontSize: 12 },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      force: { repulsion: 600, edgeLength: [100, 250], gravity: 0.05, friction: 0.1 },
      roam: true,
      draggable: true,
      symbolSize: (value, params) => {
        const sizeMap = { APT_GROUP: 38, MALWARE: 28, CVE: 26, TECHNIQUE: 24, COUNTRY: 24, CAMPAIGN: 30, TOOL: 22, INDUSTRY: 22, PERSON: 20, ORGANIZATION: 24 };
        return sizeMap[params.data?._type] || 24;
      },
      label: {
        show: true,
        position: 'bottom',
        fontSize: 10,
        color: '#c9d1d9',
        offset: [0, 4],
        formatter: params => params.data?.name || '',
      },
      edgeLabel: {
        show: true,
        formatter: params => params.data?.label || '',
        fontSize: 9,
        color: '#6e7681',
      },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 8],
      lineStyle: { color: '#30363d', width: 1.5, curveness: 0.2, opacity: 0.6 },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 2.5, opacity: 1 },
      },
      blur: { opacity: 0.2 },
      categories: [
        { name: 'APT组织', itemStyle: { color: '#ef4444' } },
        { name: '恶意软件', itemStyle: { color: '#f59e0b' } },
        { name: '工具', itemStyle: { color: '#eab308' } },
        { name: '漏洞', itemStyle: { color: '#a855f7' } },
        { name: '攻击技术', itemStyle: { color: '#3b82f6' } },
        { name: '国家', itemStyle: { color: '#22c55e' } },
        { name: '行业', itemStyle: { color: '#14b8a6' } },
        { name: '人员', itemStyle: { color: '#ec4899' } },
        { name: '攻击活动', itemStyle: { color: '#8b5cf6' } },
        { name: '组织', itemStyle: { color: '#6b7280' } },
      ],
      data: nodes.map(n => ({
        id: n.id,
        name: n.name,
        _type: n.type,
        _conf: n.confidence,
        _desc: n.description,
        symbolSize: n.id === selectedId ? 44 : undefined,
        category: (() => { const m = { APT_GROUP:0, MALWARE:1, TOOL:2, CVE:3, TECHNIQUE:4, COUNTRY:5, INDUSTRY:6, PERSON:7, CAMPAIGN:8, ORGANIZATION:9 }; return m[n.type] ?? 0; })(),
        itemStyle: n.id === selectedId ? { borderColor: '#fff', borderWidth: 3, shadowBlur: 10, shadowColor: 'rgba(255,255,255,0.3)' } : undefined,
      })),
      links: edges.map(e => ({
        source: e.source,
        target: e.target,
        label: e.label || e.type,
        lineStyle: { color: '#30363d', width: 1.5 - (1 - e.confidence) * 0.5 },
      })),
      zoom: 1.2,
    }],
    backgroundColor: 'transparent',
  }), [nodes, edges, selectedId]);

  return (
    <ReactECharts
      option={option}
      style={{ height: '100%', width: '100%' }}
      onEvents={{
        click: params => {
          if (params.dataType === 'node' && params.data?.id) {
            onNodeClick?.(nodes.find(n => n.id === params.data.id) || { id: params.data.id, name: params.data.name, type: 'UNKNOWN', confidence: 0 });
          }
        },
      }}
      opts={{ renderer: 'canvas' }}
    />
  );
}
