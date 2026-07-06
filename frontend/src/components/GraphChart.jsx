import React, { useRef, useEffect } from 'react';
import * as echarts from 'echarts';

export default function GraphChart({ nodes, edges, selectedId, onNodeClick }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  useEffect(() => {
    if (!containerRef.current) return;

    const w = containerRef.current.clientWidth;
    const h = containerRef.current.clientHeight;
    if (w === 0 || h === 0) {
      const timer = setTimeout(() => {
        if (containerRef.current) initChart();
      }, 50);
      return () => clearTimeout(timer);
    }

    initChart();
    return () => chartRef.current?.dispose();
  }, []);

  const initChart = () => {
    if (chartRef.current) chartRef.current.dispose();
    chartRef.current = echarts.init(containerRef.current, null, { renderer: 'canvas' });
    chartRef.current.on('click', params => {
      if (params.dataType === 'node' && params.data?.id) {
        const current = nodesRef.current;
        onNodeClick?.(current.find(n => n.id === params.data.id) || { id: params.data.id, name: params.data.name, type: 'UNKNOWN', confidence: 0 });
      }
    });
  };

  useEffect(() => {
    if (!chartRef.current) return;
    const categories = [
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
    ];
    const catMap = { APT_GROUP: 0, MALWARE: 1, TOOL: 2, CVE: 3, TECHNIQUE: 4, COUNTRY: 5, INDUSTRY: 6, PERSON: 7, CAMPAIGN: 8, ORGANIZATION: 9 };
    const sizeMap = { APT_GROUP: 38, MALWARE: 28, CVE: 26, TECHNIQUE: 24, COUNTRY: 24, CAMPAIGN: 30, TOOL: 22, INDUSTRY: 22, PERSON: 20, ORGANIZATION: 24 };

    chartRef.current.setOption({
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
        force: { repulsion: 600, edgeLength: [100, 250], gravity: 0.05, friction: 0.1, initSpeed: 30, coolDown: 500 },
        roam: true,
        draggable: true,
        animation: false,
        symbolSize: (_v, params) => sizeMap[params.data?._type] || 24,
        label: { show: true, position: 'bottom', fontSize: 10, color: '#c9d1d9', offset: [0, 4] },
        edgeLabel: { show: true, fontSize: 9, color: '#6e7681', formatter: p => p.data?.label || '' },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        lineStyle: { color: '#484f58', width: 1.5, curveness: 0.2, opacity: 0.8 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 2.5, opacity: 1 } },
        blur: { opacity: 0.2 },
        categories,
        data: nodes.map(n => ({
          id: n.id, name: n.name,
          _type: n.type, _conf: n.confidence, _desc: n.description,
          symbolSize: n.id === selectedId ? 44 : undefined,
          category: catMap[n.type] ?? 0,
          itemStyle: n.id === selectedId ? { borderColor: '#fff', borderWidth: 3, shadowBlur: 10, shadowColor: 'rgba(255,255,255,0.3)' } : undefined,
        })),
        links: edges.map(e => ({
          source: e.source, target: e.target,
          label: e.label || e.type,
          lineStyle: { color: '#484f58', width: 1.5 - (1 - (e.confidence || 0.5)) * 0.5 },
        })),
        zoom: 1.2,
      }],
      backgroundColor: 'transparent',
    }, true);
  }, [nodes, edges, selectedId]);

  useEffect(() => {
    const handleResize = () => chartRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
}
