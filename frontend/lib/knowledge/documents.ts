/**
 * Curated metadata and real text content for the indexed enterprise policy documents.
 * Backed by data/document_registry.json and data/documents/* in the repository.
 */

export interface PolicyDocument {
  id: string;
  filename: string;
  title: string;
  category: 'Attendance' | 'Benefits' | 'Leave' | 'Travel & Expenses';
  chunkCount: number;
  version: string;
  lastIngestedAt: string;
  fileType: 'txt' | 'md';
  summary: string;
  fullContent: string;
}

export const INDEXED_POLICY_DOCUMENTS: PolicyDocument[] = [
  {
    id: 'travel_policy',
    filename: 'travel_policy.md',
    title: 'Corporate Travel and Expense Policy',
    category: 'Travel & Expenses',
    chunkCount: 4,
    version: 'bd3fc0b5',
    lastIngestedAt: '2026-10-16T09:22:36Z',
    fileType: 'md',
    summary: 'Travel authorization rules, flight class policies, lodging caps ($200/night), and meal per diems ($75 domestic, $100 international).',
    fullContent: `# Corporate Travel and Expense Policy

## Travel Authorization
All business travel must receive written manager pre-approval at least 14 days before booking flights or lodging.

## Flight Bookings
Employees must book Economy class for domestic flights and international flights under 6 hours duration. Business class bookings are permitted only for continuous flights exceeding 8 hours with VP approval.

## Per Diem and Meals
The company provides a meal per diem allowance of $75 per travel day for domestic travel and $100 per day for international travel. Itemized receipts are required for all meal expenses.

## Lodging and Transportation
Hotel bookings should not exceed the standard corporate rate of $200 per night excluding taxes. Ground transportation should prioritize public transit, airport shuttles, or standard rideshares.`,
  },
  {
    id: 'leave_policy',
    filename: 'leave_policy.txt',
    title: 'Employee Leave Policy',
    category: 'Leave',
    chunkCount: 2,
    version: '7c8f9931',
    lastIngestedAt: '2026-10-16T09:22:36Z',
    fileType: 'txt',
    summary: '24 days annual leave allowance, maximum 10 days carry-forward expiring March 31, and emergency leave rules.',
    fullContent: `Employee Leave Policy

Annual Leave:
Employees receive 24 days of annual leave per calendar year.

Carry Forward:
Employees may carry forward a maximum of 10 unused annual leave days into the following calendar year.

Carry-forward days must be used by March 31 of the following year.

Approval:
Annual leave requests must be submitted through the employee portal and approved by the employee's manager.

Emergency Leave:
Employees may request emergency leave when unexpected personal circumstances require immediate time away from work.`,
  },
  {
    id: 'benefits_policy',
    filename: 'benefits_policy.txt',
    title: 'Employee Benefits and Perks Policy',
    category: 'Benefits',
    chunkCount: 4,
    version: 'f214d0dc',
    lastIngestedAt: '2026-10-16T09:22:36Z',
    fileType: 'txt',
    summary: 'Comprehensive healthcare coverage, 100% 401(k) match up to 4% with immediate vesting, $500 wellness stipend, and $3,000 tuition aid.',
    fullContent: `Employee Benefits and Perks Policy

Healthcare Coverage:
Comprehensive medical, dental, and vision insurance coverage begins on the first day of the calendar month following the employee start date.

Retirement 401(k) Match:
The company matches 100% of employee 401(k) contributions up to 4% of total base salary. Matching funds vest immediately upon contribution.

Wellness and Fitness Stipend:
Full-time employees are eligible for an annual wellness reimbursement of up to $500 per calendar year for gym memberships, fitness equipment, or wellness activities.

Tuition Reimbursement:
Employees pursuing job-related degree programs or technical certifications may receive up to $3,000 annually upon maintaining a passing grade.`,
  },
  {
    id: 'attendance_policy',
    filename: 'attendance_policy.txt',
    title: 'Attendance and Working Hours Policy',
    category: 'Attendance',
    chunkCount: 3,
    version: 'fbbdf653',
    lastIngestedAt: '2026-10-16T09:22:36Z',
    fileType: 'txt',
    summary: 'Standard 40 hours/week, core collaboration hours 10:00 AM - 4:00 PM local time, portal logging, and absence reporting before 9:30 AM.',
    fullContent: `Attendance and Working Hours Policy

Working Hours:
Standard full-time employee working hours are 40 hours per week, Monday through Friday.

Core Hours:
All employees must be available and reachable during core collaboration hours from 10:00 AM to 4:00 PM local time.

Attendance Logging:
Employees must log daily work hours and attendance through the internal HR portal by the end of each pay period.

Tardiness and Absences:
Unplanned absences or tardiness exceeding 30 minutes must be reported directly to the employee's manager before 9:30 AM on the day of occurrence.`,
  },
];
