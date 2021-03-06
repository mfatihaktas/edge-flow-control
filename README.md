## Background
Edge has been proposed to address the low latency and increasingly large data requirements of modern applications.
In a nutshell, edge computing refers to using the edge clusters for running user facing services that otherwise cannot tolerate the high-latency and limited-bandwidth link to the central cloud.

Here are the main areas in which edge clusters differ from the central cloud:
* Edge is close to users, i.e., propagation delay between the users and an edge cluster is less than 1 ms.
* Edge clusters have (much) lower capacity for computing and storage.


## Problem
In the central cloud, when the user demand exceeds the available service capacity, the number of servers is increased (i.e., service is horizontally scaled up) to meet the demand. On the other hand, edge clusters do not have the resources to simply horizontally scale up.

Excessive demand, if not addressed in a timely manner, will lead to contention at the system resources. Note that resource contention implies large delays, hence poor quality of service.


## Solution in general
There are essentially two ways to handle the excessive user demand (beyond utilizing the maximum available system capacity).

**Backpressuring**: One approach is to reduce the demand via backpressuring. In this, users will be informed about the resource contention and they will be asked to reduce their demand. For instance, computer networks employ flow/congestion control on the user traffic in order to prevent contention at the receivers/routers.
Backpressuring however might degrade the quality of service. For instance, real time applications are required to respond to user/client queries within a time limit, and failing to do so would reduce user satisfaction.

**Load balancing**: Another approach is to split the load across multiple service instances running on separate clusters. For instance, many popular cloud services are hosted across multiple data centers.
In the edge context, service instances run on separate edge clusters, and possibly, also on the central cloud.


## Handling the excessive demand in edge
Due to user mobility/clustering, some edge clusters will experience temporary phases of excessive load. Our goal in this project is to address the excessive load on the edge clusters. In addressing the problem, we will explore both solution alternatives: backpressuring and load balancing.

We consider the following context for the application and system characteristics:
* User-facing services are hosted on the clusters, and they implement stateless servers. That is, they do not keep any application state but simply reply to the requests received from the clients. Each service instance can be deployed as a single server or as a (Kubernetes) replica set.
* Client processes run on the user devices, and they generate requests over time. Each request is independent from the others. The performance requirement for clients is to send out requests "frequently" and receive replies for them "fast".

### Centralized architecture:
* Entire system

### Distributed architecture with end-to-end flow control:
