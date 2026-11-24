from app.schemas.auth import ( UserRegister, UserLogin, UserResponse, Token, TokenData)
from app.schemas.employee import ( EmployeeCreate, EmployeeUpdate, EmployeePatch, EmployeeResponse)
from app.schemas.department import ( DepartmentCreate, DepartmentUpdate, DepartmentResponse)
from app.schemas.leave import ( LeaveCreate, LeaveDecision, LeaveResponse)
from app.schemas.attendance import ( AttendanceManualCreate, AttendanceResponse)
from app.schemas.employee_document import EmployeeDocumentResponse