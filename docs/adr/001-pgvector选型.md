# ADR-001: 向量数据库选型 — pgvector vs Milvus

**状态**：已采纳
**日期**：2026-05
**决策者**：项目作者

## 背景

KnowFlow 是企业知识库 RAG 系统，需要存储文档分块的向量并支持相似度检索。向量数据库的选型直接影响检索性能、运维复杂度和数据一致性。

## 候选方案

| 方案 | 类型 | 特点 |
|------|------|------|
| **pgvector** | PostgreSQL 扩展 | 向量存关系库，复用现有 PG |
| Milvus | 专用向量数据库 | 原生 HNSW，高性能 |
| Qdrant | 专用向量数据库 | Rust 实现，轻量 |
| ChromaDB | 嵌入式向量数据库 | 开发友好，适合原型 |

## 对比分析

### 1. 数据一致性

KnowFlow 的检索需要权限过滤——用户只能检索有权限的文档。

- **pgvector**：`SELECT ... FROM chunks JOIN documents JOIN document_permissions WHERE ...` 一条 SQL 搞定，权限和向量在同一事务，强一致。
- **Milvus/Qdrant**：需要 metadata filter，权限信息要同步到向量库的元数据。文档权限变更时，要同时更新 PG 和向量库，存在双写一致性问题。
- **ChromaDB**：同理，metadata filter 能力弱于 SQL。

**结论**：pgvector 在权限一致性上有压倒性优势。

### 2. 运维成本

- **pgvector**：零额外服务，复用已有的 PostgreSQL，一个容器搞定。
- **Milvus**：独立服务，依赖 etcd + MinIO，至少 3 个容器。
- **Qdrant**：独立服务，1 个容器，但仍需额外维护。
- **ChromaDB**：独立服务，1 个容器。

**结论**：pgvector 运维成本最低。KnowFlow 的 VPS 只有 1vCPU/2GB，省一个服务就是省一份内存。

### 3. 性能

| 规模 | pgvector (HNSW) | Milvus |
|------|-----------------|--------|
| 1 万 chunk | <10ms | <5ms |
| 10 万 chunk | 10-50ms | <10ms |
| 100 万 chunk | 50-200ms | <20ms |
| 1000 万 chunk | 200ms+，HNSW 构建慢 | <50ms |

**结论**：十万级 chunk pgvector 够用，企业知识库通常在这个量级。千万级时 Milvus 有明显优势。

### 4. 混合检索

KnowFlow 需要向量检索 + BM25 全文检索。

- **pgvector**：BM25 用 PostgreSQL 原生 tsvector，同一数据库同一查询里可以 UNION 两路结果。
- **Milvus**：不支持全文检索，需要另外维护 Elasticsearch 或 PG 做 BM25，再在应用层融合。

**结论**：pgvector 让双路检索的实现大幅简化——两路都在一个库里。

## 决策

**采用 pgvector。**

## 后果

### 正面

- 权限过滤用 SQL JOIN，强一致，无双写问题。
- 双路检索（向量+BM25）在同一数据库完成，RRF 融合在应用层实现。
- 运维简单，不增加额外服务。
- 事务一致性——文档删除时，chunks 和向量在一个事务里级联删除。

### 负面

- 千万级 chunk 时 HNSW 索引构建慢（分钟级），需要离线构建。
- 极大规模下召回延迟不如专用向量库。
- pgvector 的 HNSW 索引占内存，大向量表可能内存压力。

### 迁移条件

当满足以下任一条件时，考虑迁移到 Milvus/Qdrant：
- chunk 数量超过 500 万
- HNSW 索引构建时间超过 30 分钟
- 召回延迟 P95 超过 200ms

迁移方案：应用层抽象 `VectorStore` 接口，pgvector 和 Milvus 各实现一个，通过配置切换。
