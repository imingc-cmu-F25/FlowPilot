import { Link } from "react-router";
import { Zap, Clock, Webhook, Calendar, Mail, Bell, Code, ArrowRight, CheckCircle, Activity } from "lucide-react";

export function Home() {
  const features = [
    {
      icon: Clock,
      title: "Time-based Triggers",
      description: "Schedule workflows to run automatically at specific times or intervals",
    },
    {
      icon: Webhook,
      title: "Webhook Integration",
      description: "Connect with external services and trigger workflows from anywhere",
    },
    {
      icon: Calendar,
      title: "Calendar Sync",
      description: "Automate tasks based on your Google Calendar events",
    },
    {
      icon: Mail,
      title: "Email Actions",
      description: "Send automated emails as part of your workflow",
    },
    {
      icon: Bell,
      title: "Smart Notifications",
      description: "Get notified instantly when your workflows execute",
    },
    {
      icon: Code,
      title: "API Integrations",
      description: "Connect to any API and automate complex tasks",
    },
  ];

  const benefits = [
    "Visual workflow builder with drag-and-drop",
    "Real-time execution monitoring",
    "Detailed logs and analytics",
    "Monthly AI-powered reports",
    "Unlimited workflow executions",
    "99.9% uptime guarantee",
  ];

  return (
    <div className="min-h-screen bg-white">
      <nav className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">FlowPilot</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/login"
                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/login"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Automate Your Workflow
            <br />
            in Minutes
          </h1>
          <p className="mx-auto max-w-2xl text-xl text-gray-600 mb-8">
            FlowPilot helps students streamline their daily tasks with powerful workflow
            automation. No coding required.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-medium text-white hover:bg-blue-700 transition-colors"
            >
              Login
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              to="/login"
              className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-base font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Register
            </Link>
          </div>
        </div>

        <div className="mt-20 rounded-2xl border border-gray-200 bg-gradient-to-br from-blue-50 to-purple-50 p-8 shadow-lg overflow-hidden">
          <div className="mx-auto max-w-4xl">
            <div className="relative h-96 rounded-lg bg-white shadow-xl p-6">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="h-40 w-40 rounded-full bg-blue-100 flex items-center justify-center">
                      <Zap className="h-20 w-20 text-blue-600" />
                    </div>
                  </div>

                  <div className="absolute -top-12 -left-12">
                    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                      <div className="flex items-center gap-3">
                        <Clock className="h-6 w-6 text-purple-600" />
                        <span className="text-sm font-medium">Time Trigger</span>
                      </div>
                    </div>
                  </div>

                  <div className="absolute -top-12 -right-12">
                    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                      <div className="flex items-center gap-3">
                        <Webhook className="h-6 w-6 text-green-600" />
                        <span className="text-sm font-medium">Webhook</span>
                      </div>
                    </div>
                  </div>

                  <div className="absolute -bottom-12 -left-12">
                    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                      <div className="flex items-center gap-3">
                        <Mail className="h-6 w-6 text-blue-600" />
                        <span className="text-sm font-medium">Send Email</span>
                      </div>
                    </div>
                  </div>

                  <div className="absolute -bottom-12 -right-12">
                    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                      <div className="flex items-center gap-3">
                        <Bell className="h-6 w-6 text-orange-600" />
                        <span className="text-sm font-medium">Notify</span>
                      </div>
                    </div>
                  </div>

                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                    <Activity className="h-8 w-8 text-blue-600" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Everything You Need to Automate
            </h2>
            <p className="text-lg text-gray-600">
              Powerful features designed for students and productivity enthusiasts
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50">
                    <Icon className="h-6 w-6 text-blue-600" />
                  </div>
                  <h3 className="mb-2 text-lg font-semibold text-gray-900">{feature.title}</h3>
                  <p className="text-sm text-gray-600">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-6">
                Why Choose FlowPilot?
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Built specifically for students who want to save time and focus on what matters
                most. FlowPilot makes automation accessible to everyone.
              </p>
              <div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-50">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <span className="text-gray-700">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-gradient-to-br from-purple-50 to-blue-50 p-8 flex items-center justify-center">
              <div className="relative h-80 w-full">
                <div className="absolute left-1/4 top-1/4">
                  <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      <span className="text-sm font-medium">Workflow Active</span>
                    </div>
                  </div>
                </div>

                <div className="absolute right-1/4 top-1/3">
                  <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                    <div className="flex items-center gap-2">
                      <Activity className="h-5 w-5 text-blue-600" />
                      <span className="text-sm font-medium">Running</span>
                    </div>
                  </div>
                </div>

                <div className="absolute left-1/3 bottom-1/4">
                  <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
                    <div className="flex items-center gap-2">
                      <Code className="h-5 w-5 text-purple-600" />
                      <span className="text-sm font-medium">Automated</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-gray-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900">FlowPilot</span>
            </div>
            <p className="text-sm text-gray-600">© 2026 FlowPilot. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
