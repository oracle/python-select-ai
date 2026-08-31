    # Google Cloud deployment modes

Select AI supports two distinct Google Cloud deployment modes. Choose based on
whether the database and Select AI team are known at deployment time or must
be selected dynamically by each user.

| | Standalone | Dynamic gateway |
| --- | --- | --- |
| Database and team | Fixed at deployment time | Chosen at runtime for each user session |
| Public A2A service | One service for one configured team | One gateway that presents an A2UI connection form |
| Users | All requests use the deployed database identity | Any permitted user can connect to a reachable Oracle database and Select AI team |
| Architecture | One Cloud Run service | Cloud Run gateway, plus Consul and worker replicas in GKE |
| Session isolation | Shared service database pool | One child process and async pool per active user session |
| Main benefit | Simple, predictable deployment | Dynamic, multi-database and multi-team access from one A2A endpoint |
| Operational cost | Low | Higher: GKE workers, Consul, routing, TTL, and session capacity |

Use [standalone](standalone/README.md) when a service should expose one known
database team. Use [gateway](gateway/README.md) when users must dynamically
choose their database connection and team.
