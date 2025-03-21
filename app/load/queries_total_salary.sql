WITH RECURSIVE TeamSalary AS (
    -- Base case: Every employee starts with their own salary
    SELECT
        id,
        manager_id,
        salary,
        salary AS TotalTeamSalary
    FROM employees
    UNION ALL
    -- Recursive case: Add subordinate salaries to their managers
    SELECT
        e.id,
        e.manager_id,
        e.salary,
        ts.TotalTeamSalary + e.salary
    FROM employees e
             INNER JOIN TeamSalary ts ON e.manager_id = ts.id
)
SELECT id, SUM(TotalTeamSalary) AS TotalTeamSalary
FROM TeamSalary
GROUP BY id
ORDER BY id;
