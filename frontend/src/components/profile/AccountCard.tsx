interface AccountCardProps {
  username: string;
}

export function AccountCard({ username }: AccountCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Account</h2>
      <div>
        <label className="mb-2 block text-sm font-medium text-gray-700">Username</label>
        <p className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-gray-900">
          {username}
        </p>
      </div>
    </div>
  );
}
