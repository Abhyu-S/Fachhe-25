graph TD
    A[Smart Classroom Idea] --> B{Feasibility Assessment};

    B --> C{Technical Feasibility?};
    C --> C1{Clash-Free Scheduling?};
    C --> C2{Pose Detection?};
    C --> C3{Exam Monitoring?};

    C1 -- Yes --> D{Operational Feasibility?};
    C2 -- Yes --> D;
    C3 -- Yes --> D;
    C1 -- No --> F[Re-evaluate Technical Solution];
    C2 -- No --> F;
    C3 -- No --> F;

    D --> D1{Simple Teacher/Student Access?};
    D --> D2{Scalability?};

    D1 -- Yes --> E{Economic Feasibility?};
    D2 -- Yes --> E;
    D1 -- No --> G[Re-evaluate Operational Plan];
    D2 -- No --> G;

    E --> E1{Moderate Initial Cost?};
    E --> E2{High ROI (Return on Investment)?};

    E1 -- Yes --> H[Idea is Practical and Sustainable!];
    E2 -- Yes --> H;
    E1 -- No --> I[Re-evaluate Economic Model];
    E2 -- No --> I;

    F --> B;
    G --> B;
    I --> B;
