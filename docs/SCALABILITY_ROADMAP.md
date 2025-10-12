# 📊 NEXA Platform Scalability Roadmap
**Version:** 1.0  
**Last Updated:** October 9, 2025  
**Goal:** Scale from MVP to National Platform (100,000+ users)

---

## 🎯 Executive Summary

### Vision
Transform NEXA from single-contractor tool to **national platform serving every PG&E contractor**

### Timeline
- **Phase 1 (Months 1-6):** MVP to First 100 Customers
- **Phase 2 (Months 7-18):** Regional Growth (1,000 Customers)
- **Phase 3 (Months 19-36):** National Scale (10,000+ Customers)

### Investment Required
- Phase 1: $5,000 (infrastructure + domain)
- Phase 2: $50,000 (engineering + marketing)
- Phase 3: $500,000 (team + infrastructure + sales)

---

## 📈 Phase 1: MVP to Product-Market Fit (Months 1-6)

### Target Metrics
```
Users: 10-100 contractors
Monthly API Calls: 1,000-10,000
Revenue: $500-5,000/month ($50/user/month)
Uptime: 95%+
Response Time: <2 seconds
```

### Infrastructure
**Current Setup (KEEP):**
```yaml
Platform: Render.com
Plan: Standard ($21/month) → Pro ($85/month as needed)
Architecture: Single Docker container
Model: sentence-transformers (self-hosted)
Database: File-based (pickle/json)
Storage: /data persistent disk (100GB)
CDN: Render CDN (included)
```

### Cost Breakdown
```
Infrastructure: $85/month
Domain/SSL: $15/year
Total: ~$1,000/year
```

### Decision Triggers → Phase 2
✅ **GO Signal:**
- 50+ paying customers
- $2,500+/month recurring revenue
- <5% churn rate
- 90%+ uptime for 3 months
- API usage >50,000 calls/month

❌ **WAIT Signal:**
- <20 paying customers after 6 months
- High churn (>20%/month)
- Poor product-market fit signals

### Engineering Team
- 1 Full-stack developer (you)
- Outsource: UI/UX design as needed

---

## 🚀 Phase 2: Regional Growth (Months 7-18)

### Target Metrics
```
Users: 100-1,000 contractors
Monthly API Calls: 100,000-500,000
Revenue: $5,000-50,000/month
Uptime: 99%+
Response Time: <1 second
Team: 2-3 people
```

### Infrastructure Upgrade
**Hybrid Architecture:**

```yaml
API Layer:
  Platform: Render.com OR AWS/GCP
  Setup: 3-5 auto-scaling containers
  Load Balancer: Render (included) or AWS ALB
  
ML Inference:
  Primary: Self-hosted (Phi-3/Llama 3.2)
  Fallback: OpenAI API (5-10% of requests)
  GPU: Optional - Render GPU ($150/month) or CPU cluster
  
Database:
  Primary: PostgreSQL (Render managed)
  Caching: Redis (Render add-on)
  File Storage: AWS S3 or Render disk
  
Monitoring:
  Platform: Better Uptime or Sentry
  Logs: Render native logs
  Alerts: PagerDuty or Discord webhooks
```

### Cost Breakdown (Monthly)
```
API Servers: $250-500 (3-5 instances)
ML Inference: $150-300 (GPU or CPU cluster)
Database: $50-100 (managed PostgreSQL)
Redis Cache: $25-50
File Storage: $20-50 (S3)
OpenAI API: $100-500 (fallback only)
Monitoring: $50-100
CDN: $0-50 (Cloudflare free tier usually enough)

TOTAL: $645-1,650/month
Revenue Target: $5,000-50,000/month
Margin: 70-90%
```

### ML Strategy: Hybrid Model
**Self-Hosted (80% of requests):**
- Document verification
- Classification/tagging
- Simple text extraction
- Batch processing

**API-Based (20% of requests):**
- Complex document generation
- Edge cases requiring reasoning
- Quality validation/fallback
- New feature prototyping

### Decision Triggers → Phase 3
✅ **GO Signal:**
- 500+ paying customers
- $25,000+/month recurring revenue
- <10% churn rate
- 99%+ uptime for 6 months
- Clear path to 5,000 customers
- API usage >1M calls/month
- Multiple contractor types using platform

❌ **WAIT Signal:**
- Revenue growth <20%/month
- Cannot maintain 99% uptime
- Engineering team overwhelmed
- Customer acquisition cost too high

### Engineering Team
- 1 Full-stack lead (you)
- 1 Backend/ML engineer
- 1 Frontend engineer (contract/part-time)
- 1 DevOps consultant (as needed)

---

## 🌎 Phase 3: National Scale (Months 19-36)

### Target Metrics
```
Users: 1,000-100,000 contractors
Monthly API Calls: 5M-50M
Revenue: $50,000-1,000,000/month
Uptime: 99.9%+
Response Time: <500ms
Team: 8-15 people
```

### Infrastructure: Enterprise Grade
**Multi-Region Kubernetes Cluster:**

```yaml
Infrastructure:
  Platform: AWS/GCP/Azure
  Orchestration: Kubernetes (EKS/GKE/AKS)
  Regions: 2-3 (US-West, US-East, US-Central)
  
API Layer:
  Instances: 20-100 auto-scaling pods
  Load Balancer: AWS ALB with CloudFlare WAF
  CDN: CloudFlare Enterprise
  Rate Limiting: Kong or Traefik
  
ML Inference:
  GPU Cluster: 10-50 GPU nodes (NVIDIA T4/A10)
  Auto-scaling: HPA based on queue depth
  Model Serving: TensorFlow Serving or TorchServe
  Fallback: OpenAI API (<5% of traffic)
  
Database:
  Primary: PostgreSQL Cluster (RDS Multi-AZ)
  Read Replicas: 3-5
  Caching: Redis Cluster (ElastiCache)
  Search: Elasticsearch for logs/analytics
  
Storage:
  Documents: S3 with lifecycle policies
  Backups: Automated daily snapshots
  CDN: S3 + CloudFront
  
Monitoring & Observability:
  APM: Datadog or New Relic
  Logging: ELK Stack or Datadog Logs
  Alerting: PagerDuty with escalation
  Tracing: Jaeger or Zipkin
  Metrics: Prometheus + Grafana
```

### Cost Breakdown (Monthly)
```
Compute (API + ML): $15,000-25,000
  - API pods: $5,000-8,000
  - GPU cluster: $10,000-17,000

Database & Storage: $3,000-5,000
  - PostgreSQL: $1,500-2,500
  - Redis: $500-1,000
  - S3/Storage: $1,000-1,500

Network & CDN: $2,000-5,000
  - Load balancers: $500-1,000
  - CloudFlare: $1,000-3,000
  - Data transfer: $500-1,000

Monitoring & Tools: $1,000-2,000
  - Datadog: $500-1,000
  - PagerDuty: $200-400
  - Other tools: $300-600

OpenAI API (Fallback): $1,000-3,000
  - Edge cases only
  - <5% of total requests

Contingency: $2,000-5,000

TOTAL: $24,000-45,000/month
Revenue Target: $50,000-1,000,000/month
Target Margin: 50-70%
```

### ML Strategy: Mostly Self-Hosted
**Self-Hosted (95% of requests):**
- All core features
- Custom fine-tuned models
- Real-time inference
- Batch processing
- **Cost:** $0.001-0.005 per request

**API-Based (5% of requests):**
- Ultra-complex edge cases
- Quality validation
- Experimental features
- **Cost:** $0.01-0.05 per request

### Engineering Team
```
Leadership:
- 1 CTO/VP Engineering
- 1 Product Manager

Engineering:
- 3 Backend Engineers
- 2 Frontend Engineers
- 2 ML Engineers
- 2 DevOps/SRE Engineers
- 1 Mobile Engineer

Support:
- 2 Customer Success
- 1 Technical Writer
- 1 QA Engineer
```

### Decision Triggers → IPO/Exit
✅ **Signals:**
- 10,000+ paying customers
- $500,000+/month recurring revenue
- Market leader in PG&E contractor space
- Expansion to other utilities
- Healthy margins (>50%)
- Strong retention (>90%)

---

## 🎯 Critical Decision Points

### When to Switch from Self-Hosted to API?
**NEVER fully switch. Always hybrid.**

**Use API more when:**
- Engineering team bandwidth constrained
- Growth rate >100%/month (can't scale infra fast enough)
- Margins >70% (can afford variable costs)
- New feature exploration

**Use Self-Hosted more when:**
- Margins <50% (need to reduce costs)
- Stable feature set (no rapid changes)
- Privacy/compliance requirements
- Large engineering team

### When to Hire ML Engineer?
**Trigger:** Any of these:
- Revenue >$25,000/month
- >500,000 API calls/month
- Need custom model fine-tuning
- API costs >$2,000/month

### When to Move from Render to AWS/GCP?
**Trigger:** Any of these:
- Revenue >$50,000/month
- Need multi-region deployment
- Require <500ms latency globally
- Render limits hit (CPU/memory)
- Complex networking requirements

---

## 💰 Unit Economics Calculator

### Key Metrics to Track
```python
# Per-User Economics
COGS_per_user_per_month = {
    "Phase 1 (MVP)": {
        "infrastructure": 0.85,      # $85 / 100 users
        "api_calls": 0.00,          # Self-hosted
        "support": 0.00,            # Self-service
        "total": 0.85
    },
    "Phase 2 (Regional)": {
        "infrastructure": 1.65,      # $1,650 / 1,000 users
        "api_calls": 0.50,          # Hybrid approach
        "support": 2.00,            # Part-time support
        "total": 4.15
    },
    "Phase 3 (National)": {
        "infrastructure": 4.50,      # $45,000 / 10,000 users
        "support": 5.00,            # Full support team
        "sales": 3.00,              # Sales team
        "total": 12.50
    }
}

# Target Pricing
price_per_user = 50-75  # per month

# Gross Margin
Phase 1: (50 - 0.85) / 50 = 98%
Phase 2: (50 - 4.15) / 50 = 92%
Phase 3: (50 - 12.50) / 50 = 75%
```

### Break-Even Analysis
```
Phase 1: 
  - Fixed costs: $1,000/month (infra + you)
  - Break-even: 20 users at $50/month
  
Phase 2:
  - Fixed costs: $20,000/month (team + infra)
  - Break-even: 400 users at $50/month
  
Phase 3:
  - Fixed costs: $120,000/month (team + infra + sales)
  - Break-even: 2,400 users at $50/month
```

---

## 🚨 Risk Mitigation

### Technical Risks

**Risk: Self-hosted model accuracy degrades**
- **Mitigation:** API fallback for low-confidence results
- **Trigger:** <80% accuracy on test set
- **Cost:** <10% increase in COGS

**Risk: Traffic spike crashes system**
- **Mitigation:** Auto-scaling + rate limiting
- **Monitoring:** Alert at 70% capacity
- **Backup:** Maintenance mode page ready

**Risk: Data loss**
- **Mitigation:** Daily backups to S3
- **Testing:** Monthly restore drills
- **SLA:** <1 hour recovery time

### Business Risks

**Risk: Large competitor enters market**
- **Mitigation:** Focus on PG&E-specific features
- **Moat:** Custom models trained on YOUR data
- **Speed:** Ship features 2x faster

**Risk: Customers don't pay**
- **Mitigation:** Prepay monthly, auto-suspend
- **Grace period:** 7 days
- **Collections:** Automated dunning

**Risk: Unit economics worsen**
- **Mitigation:** Monthly cost reviews
- **Trigger:** Gross margin <60%
- **Actions:** Raise prices OR optimize infra

---

## 📊 Success Metrics Dashboard

### Must Track Monthly
```
Revenue Metrics:
✓ MRR (Monthly Recurring Revenue)
✓ New MRR
✓ Churned MRR
✓ Net MRR Growth Rate

Usage Metrics:
✓ Active Users (DAU/MAU)
✓ API Calls per User
✓ Documents Processed
✓ Average Response Time

Cost Metrics:
✓ Infrastructure Costs
✓ API Costs (OpenAI)
✓ Cost per User
✓ Gross Margin %

Quality Metrics:
✓ Model Accuracy
✓ Error Rate
✓ Support Tickets
✓ NPS Score

Technical Metrics:
✓ Uptime %
✓ P95 Latency
✓ Error Rate
✓ Failed Deployments
```

---

## 🎯 Next 90 Days Action Items

### Month 1 (Weeks 1-4)
**Goal:** Stabilize Current Infrastructure

Week 1-2:
- [x] Document verification deployed ✅
- [ ] Add monitoring (Better Uptime free tier)
- [ ] Create backup/restore procedures
- [ ] Set up error tracking (Sentry free tier)

Week 3-4:
- [ ] Build PM upload interface
- [ ] Add document verification endpoint
- [ ] Create simple admin dashboard
- [ ] First 5 beta customers

### Month 2 (Weeks 5-8)
**Goal:** Build GF Dashboard + Get to 10 Customers

Week 5-6:
- [ ] GF kanban board (Needs Pre-field, Needs Scheduled)
- [ ] Job assignment workflow
- [ ] Mobile app integration
- [ ] 10 paying customers ($500 MRR)

Week 7-8:
- [ ] Scheduling intelligence (crew availability)
- [ ] Basic analytics dashboard
- [ ] Customer feedback loop
- [ ] Iterate on UX

### Month 3 (Weeks 9-12)
**Goal:** Add Document Completion + Get to 25 Customers

Week 9-10:
- [ ] Add Phi-3 model for document completion
- [ ] Test on foreman workflows
- [ ] File naming automation
- [ ] 20 paying customers ($1,000 MRR)

Week 11-12:
- [ ] Fine-tune on collected job data
- [ ] Measure accuracy improvements
- [ ] Marketing push
- [ ] 25 customers ($1,250 MRR)

### Success Criteria (90 Days)
```
✅ 25+ paying customers
✅ $1,250+ MRR
✅ <10% churn
✅ 95%+ uptime
✅ All features working
✅ Positive customer feedback
```

---

## 📝 Quarterly Review Template

### Q1 Review Checklist
```
Revenue:
[ ] Did we hit MRR target?
[ ] Is growth rate >20%/month?
[ ] Is churn <15%?

Product:
[ ] Are customers happy? (NPS >30)
[ ] Are features being used?
[ ] Any major bugs?

Technical:
[ ] Uptime >95%?
[ ] Response time <2s?
[ ] Any scaling issues?

Decision:
[ ] CONTINUE to Phase 2?
[ ] PIVOT features?
[ ] PAUSE and optimize?
```

---

## 🚀 Phase Transition Checklist

### Before Moving to Phase 2
```
Revenue:
✅ $2,500+ MRR
✅ 50+ paying customers
✅ <10% monthly churn
✅ 6 months of runway

Technical:
✅ 99% uptime last 90 days
✅ Monitoring in place
✅ Backups tested
✅ Can handle 2x traffic

Team:
✅ Process documented
✅ Can hire engineer
✅ Customer support scalable

Legal/Business:
✅ Terms of service
✅ Privacy policy
✅ Insurance (E&O)
✅ Proper business entity
```

### Before Moving to Phase 3
```
Revenue:
✅ $25,000+ MRR
✅ 500+ customers
✅ <5% monthly churn
✅ 12 months runway

Technical:
✅ 99.5% uptime last 6 months
✅ Can handle 10x traffic
✅ Multi-region ready
✅ Enterprise security

Team:
✅ 3+ engineers
✅ 1 PM
✅ Customer success team
✅ DevOps expertise

Market:
✅ Clear market leader
✅ Multiple contractor types
✅ Proven unit economics
✅ Competitive moat
```

---

## 🎓 Key Learnings from Similar Platforms

### Notion (100M+ users)
- Started with small self-hosted features
- Added AI via API when demand proved
- Now hybrid: search (self-hosted) + AI (API)
- **Lesson:** Start small, hybrid at scale

### Figma (4M+ users)
- Started on AWS, later moved to GCP
- Built custom infrastructure only after PMF
- **Lesson:** Use managed services until you must optimize

### Stripe (Millions of businesses)
- Over-invested in infrastructure early
- Paid off at scale but risky before PMF
- **Lesson:** Don't over-engineer too early

---

## ✅ Final Recommendation

**Your Current Path: PERFECT** ✅

Stay self-hosted through Phase 1:
- Fastest to market
- Total control
- Learn what customers actually need
- Minimal costs

Add hybrid approach in Phase 2:
- Scale what works
- API for edge cases
- Best economics

Build for national scale in Phase 3:
- By then you'll know exactly what you need
- Have budget and team to do it right
- Proven product-market fit

---

**Next Step:** Focus on getting to 10 paying customers in next 30 days. Everything else is premature optimization! 🚀

---

*Document Owner: Mike V*  
*Review Cadence: Quarterly*  
*Version History: See git log*
