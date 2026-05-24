import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();

    const response = await fetch("http://127.0.0.1:5000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json({
      success: false,
      error: "Cannot connect to AI model. Make sure Flask is running."
    }, { status: 500 });
  }
}

export async function GET() {
  try {
    const response = await fetch("http://127.0.0.1:5000/options");
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({}, { status: 500 });
  }
}