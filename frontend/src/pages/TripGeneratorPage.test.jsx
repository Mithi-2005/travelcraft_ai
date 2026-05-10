import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { getDestinationSuggestions } from "../lib/api";
import { APP_CURRENCY_CODE, formatCurrency } from "../lib/currency";
import TripGeneratorPage from "./TripGeneratorPage";

const mockCreateTrip = vi.fn();
const baseMemory = {
  budget_preference: 2600,
  interests: ["food"],
  preferred_mood: "relaxed",
};
const mockAppContextValue = {
  createTrip: mockCreateTrip,
  isGenerating: false,
  recentPlan: null,
  memory: { ...baseMemory },
};

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
}));

vi.mock("../components/ui/MagneticButton", () => ({
  default: ({ children, ...props }) => <button {...props}>{children}</button>,
}));

vi.mock("../lib/api", () => ({
  getDestinationSuggestions: vi.fn(),
}));

vi.mock("../state/AppContext", () => ({
  useAppContext: () => mockAppContextValue,
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <TripGeneratorPage />
    </MemoryRouter>,
  );
}

function submitGeneratorForm() {
  const submitButton = screen.getByRole("button", { name: /generate trip/i });
  const form = submitButton.closest("form");
  expect(form).not.toBeNull();
  fireEvent.submit(form);
}

describe("TripGeneratorPage", () => {
  beforeEach(() => {
    mockCreateTrip.mockReset();
    getDestinationSuggestions.mockReset();
    getDestinationSuggestions.mockResolvedValue([]);
    mockAppContextValue.isGenerating = false;
    mockAppContextValue.recentPlan = null;
    mockAppContextValue.memory = { ...baseMemory };
    window.localStorage.clear();
  });

  test("blocks blank destination", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "   " } });
    submitGeneratorForm();

    expect(await screen.findByText(/enter a destination/i)).toBeInTheDocument();
    expect(mockCreateTrip).not.toHaveBeenCalled();
  });

  test("blocks non-positive budget", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Tokyo" } });
    fireEvent.change(screen.getByLabelText(/budget/i), { target: { value: "0" } });
    submitGeneratorForm();

    expect(await screen.findByText(/budget must be greater than 0/i)).toBeInTheDocument();
    expect(mockCreateTrip).not.toHaveBeenCalled();
  });

  test("blocks non-positive days and traveler count", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Tokyo" } });
    fireEvent.change(screen.getByLabelText(/number of days/i), { target: { value: "0" } });
    fireEvent.change(screen.getByLabelText(/number of persons/i), { target: { value: "0" } });
    submitGeneratorForm();

    expect(await screen.findByText(/trip length must be at least 1 day/i)).toBeInTheDocument();
    expect(await screen.findByText(/traveler count must be at least 1/i)).toBeInTheDocument();
    expect(mockCreateTrip).not.toHaveBeenCalled();
  });

  test("blocks missing interests", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Tokyo" } });
    fireEvent.click(screen.getByRole("button", { name: /^food$/i }));
    submitGeneratorForm();

    expect(await screen.findByText(/select at least one interest/i)).toBeInTheDocument();
    expect(mockCreateTrip).not.toHaveBeenCalled();
  });

  test("does not show a currency selector", () => {
    renderPage();

    expect(screen.queryByLabelText("Currency")).not.toBeInTheDocument();
  });

  test("shows popular destinations before typing", async () => {
    renderPage();

    fireEvent.focus(screen.getByLabelText("Destination"));

    expect(await screen.findByText(/popular destinations/i)).toBeInTheDocument();
    expect(screen.getByText("Goa, India")).toBeInTheDocument();
    expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
  });

  test("fetches destination suggestions and lets the user pick one", async () => {
    getDestinationSuggestions.mockResolvedValue([
      {
        id: "lisbon-portugal",
        name: "Lisbon",
        country: "Portugal",
        region: "Lisbon District",
        display_name: "Lisbon, Portugal",
        description: "Sunlit hill city with tram-lined streets and riverside sunsets.",
        highlights: ["architecture", "food", "walking city"],
      },
    ]);

    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Lis" } });

    await waitFor(() => expect(getDestinationSuggestions).toHaveBeenCalledWith("Lis", 6));
    expect(await screen.findByText("Lisbon, Portugal")).toBeInTheDocument();
    expect(screen.getByText(/tram-lined streets/i)).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole("option", { name: /lisbon, portugal/i }));

    expect(screen.getByLabelText("Destination")).toHaveValue("Lisbon, Portugal");
    expect(screen.getByText(/selected destination/i)).toBeInTheDocument();
  });

  test("keeps the destination dropdown closed after a suggestion is selected", async () => {
    getDestinationSuggestions.mockResolvedValue([
      {
        id: "lisbon-portugal",
        name: "Lisbon",
        country: "Portugal",
        region: "Lisbon District",
        display_name: "Lisbon, Portugal",
        description: "Sunlit hill city with tram-lined streets and riverside sunsets.",
        highlights: ["architecture", "food", "walking city"],
      },
    ]);

    renderPage();

    const destinationInput = screen.getByLabelText("Destination");
    fireEvent.change(destinationInput, { target: { value: "Lis" } });
    await screen.findByText("Lisbon, Portugal");
    fireEvent.mouseDown(screen.getByRole("option", { name: /lisbon, portugal/i }));

    fireEvent.focus(destinationInput);

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.queryByText(/recent searches/i)).not.toBeInTheDocument();
  });

  test("reopens destination suggestions after the selected value is edited", async () => {
    getDestinationSuggestions.mockResolvedValue([
      {
        id: "lisbon-portugal",
        name: "Lisbon",
        country: "Portugal",
        region: "Lisbon District",
        display_name: "Lisbon, Portugal",
        description: "Sunlit hill city with tram-lined streets and riverside sunsets.",
        highlights: ["architecture", "food", "walking city"],
      },
    ]);

    renderPage();

    const destinationInput = screen.getByLabelText("Destination");
    fireEvent.change(destinationInput, { target: { value: "Lis" } });
    await screen.findByText("Lisbon, Portugal");
    fireEvent.mouseDown(screen.getByRole("option", { name: /lisbon, portugal/i }));

    fireEvent.change(destinationInput, { target: { value: "Lisbo" } });

    await waitFor(() => expect(getDestinationSuggestions).toHaveBeenCalledWith("Lisbo", 6));
    expect(await screen.findByRole("listbox")).toBeInTheDocument();
  });

  test("sends INR currency code with request", async () => {
    mockCreateTrip.mockResolvedValue({
      destination: "Tokyo",
      days: 5,
      traveler_count: 3,
      budget: 150,
      currency_code: APP_CURRENCY_CODE,
      interests: ["food"],
      mood: "relaxed",
      overview: "Overview",
      best_time_to_visit: "Spring",
      live_insights: [],
      attractions: [],
      itinerary: [],
      cost_breakdown: { accommodation: 10, food: 10, transport: 10, activities: 10, contingency: 10, total: 150 },
      smart_suggestions: [],
      research_mode: "fallback",
      research_sources: [],
      llm_mode: "fallback",
    });

    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Tokyo" } });
    fireEvent.change(screen.getByLabelText(/number of days/i), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText(/number of persons/i), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(/budget/i), { target: { value: "150" } });
    submitGeneratorForm();

    await waitFor(() =>
      expect(mockCreateTrip).toHaveBeenCalledWith(
        expect.objectContaining({
          destination: "Tokyo",
          days: 5,
          traveler_count: 3,
          budget: 150,
          currency_code: APP_CURRENCY_CODE,
        }),
      ),
    );
  });

  test("formats returned amounts with selected currency", async () => {
    mockCreateTrip.mockResolvedValue({
      trip_id: "trip-1",
      destination: "Tokyo",
      days: 5,
      traveler_count: 3,
      budget: 150,
      currency_code: APP_CURRENCY_CODE,
      interests: ["food"],
      mood: "relaxed",
      generated_at: "2026-01-01T00:00:00+00:00",
      overview: "Overview",
      best_time_to_visit: "Spring",
      live_insights: [],
      attractions: [{ name: "Spot", reason: "Reason", best_time: "Morning", estimated_cost: 10 }],
      itinerary: [{ day: 1, theme: "Theme", summary: "Summary", activities: [], meals: ["Meal 1", "Meal 2"], daily_estimate: 20 }],
      cost_breakdown: { accommodation: 10, food: 10, transport: 10, activities: 10, contingency: 10, total: 150 },
      smart_suggestions: [{ title: "Tip", description: "Desc" }],
      research_mode: "fallback",
      research_error: null,
      research_sources: [],
      llm_mode: "fallback",
      llm_error: null,
    });

    renderPage();

    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Tokyo" } });
    fireEvent.change(screen.getByLabelText(/number of days/i), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText(/number of persons/i), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(/budget/i), { target: { value: "150" } });
    submitGeneratorForm();

    expect((await screen.findAllByText(formatCurrency(10, APP_CURRENCY_CODE))).length).toBeGreaterThan(0);
  });
});
