import { Link } from "react-router";

interface NavDropdownLinkProps {
  to: string;
  onClick?: () => void;
  children: React.ReactNode;
}

export function NavDropdownLink({ to, onClick, children }: NavDropdownLinkProps) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
    >
      {children}
    </Link>
  );
}
