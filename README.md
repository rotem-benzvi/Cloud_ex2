# Cloud_ex2

In a real-world project, there are several failure modes that need to be addressed:

1. Endpoint and Worker Node Failures: Currently, if an Endpoint or Worker Node crashes or becomes unavailable during execution, we may lose important data. To mitigate this, we can implement the following solutions:
   - For Endpoints: Connect the Endpoint to an external storage service to persist data. This ensures that even if the Endpoint crashes, the data remains accessible.
   - For Workers: Instead of removing the work from the queue immediately after assigning it to a Worker, move it to an "InWorkerQueue." If the Worker fails to return a response within a certain timeframe, put the work back in the queue for another Worker to handle. Additionally, the Endpoint can maintain a list of completed work IDs to avoid receiving duplicate responses.

   **Note:** We have incorporated a logic in the Worker Node to verify if its parent Endpoint exists in the list of endpoints obtained from EC2 using the describe_instance_status API. If the parent Endpoint is not found, it is assumed that the parent is no longer running, and the Worker Node gracefully terminates itself. This check is performed in addition to the case where the Worker Node kills itself when there are no pending tasks to execute.

2. Max Number of Workers per Endpoint: Currently, each Endpoint has a maximum number of Workers. However, this number is not globally shared. If all calls to enqueue tasks are made against a single Endpoint, the system may not utilize the maximum allowed Workers. To address this, we can implement a mechanism to distribute the workload among multiple Nodes. For example, the Endpoint can request the other Nodes to use their available capacity or allocate Workers in case of high load.

3. Race Condition in pullCompleted: There is a potential race condition when multiple calls are made to pullCompleted simultaneously. If the other Endpoint also requests completed works at the same time, it is possible to encounter conflicts or try to delete non-existing entries from the completed works array. To handle this scenario, we should implement appropriate synchronization mechanisms to ensure data consistency and avoid conflicts.

These measures will improve the resilience, scalability, and reliability of the system in real-world scenarios.